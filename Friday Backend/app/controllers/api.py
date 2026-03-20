from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.state import state, deduplicator
from app.services.tts import speak
from app.services.stats import get_system_stats
from app.services.actions import execute_command, _execute_command_silent
from app.services.ai_router import ask_ai, get_ai_mode, set_ai_mode, is_searching
from app.services.reminders import store as reminder_store, parse_reminder_text
from app.services.calendar_service import create_calendar_event_from_text, create_ics_event, open_in_windows_calendar
from app.services.vision.air_mouse import air_mouse
from app.services.vision.sign_launcher import sign_launcher

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


class PowerToggle(BaseModel):
    state: bool

class MicToggle(BaseModel):
    state: bool

class VolumeToggle(BaseModel):
    state: bool

class SpeakRequest(BaseModel):
    text: str

class Command(BaseModel):
    text: str

class AIModeToggle(BaseModel):
    mode: str  # "general", "search", "command"

class ReminderCreate(BaseModel):
    title: str
    dueAt: str
    repeat: str = "none"

class CalendarCreate(BaseModel):
    title: str
    start: str
    durationMinutes: int = 60
    description: str = ""
    location: str = ""


@router.get("/")
async def root():
    return {
        "message": "FRIDAY Voice Assistant is running",
        "version": "1.0.0",
        "status": "operational",
    }


@router.get("/api/status")
async def get_status():
    return {
        "isPoweredOn": state.is_powered_on,
        "isSpeaking": state.is_speaking,
        "isMicOn": state.is_mic_on,
        "isVolumeOn": state.is_volume_on,
        "lastCommand": state.last_command,
        "awake": state.is_awake(),
        "stats": get_system_stats(),
        "aiMode": get_ai_mode(),
        "isSearching": is_searching(),
    }


@router.post("/api/power")
async def toggle_power(data: PowerToggle):
    if not data.state and state.is_powered_on:
        speak("Going offline, sir. It's been a pleasure serving you today. Systems powering down now.")
    state.is_powered_on = data.state
    return {"success": True, "isPoweredOn": state.is_powered_on}


@router.post("/api/mic")
async def toggle_mic(data: MicToggle):
    state.is_mic_on = data.state
    return {"success": True, "isMicOn": state.is_mic_on}


@router.post("/api/volume")
async def toggle_volume(data: VolumeToggle):
    state.is_volume_on = data.state
    return {"success": True, "isVolumeOn": state.is_volume_on}


# ─────────────────────────────────────────────
# AI Mode Toggle — 3 modes
# ─────────────────────────────────────────────
@router.get("/api/ai-mode")
async def get_ai_mode_endpoint():
    return {"success": True, "mode": get_ai_mode()}


@router.post("/api/ai-mode")
async def set_ai_mode_endpoint(data: AIModeToggle):
    try:
        set_ai_mode(data.mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    labels = {
        "general": "General AI",
        "search": "Search AI",
        "command": "Command AI",
    }
    speak(f"Switched to {labels.get(data.mode, data.mode)}, sir.")
    return {"success": True, "mode": get_ai_mode()}


@router.post("/api/speak")
async def speak_text(data: SpeakRequest):
    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")
    speak(data.text)
    return {"success": True, "text": data.text}


@router.post("/api/command")
async def receive_command(data: Command):
    command = data.text.lower().strip()
    logger.info("Received /api/command POST, command=%s, ai_mode=%s", command, get_ai_mode())

    if not command:
        raise HTTPException(status_code=400, detail="Empty command")

    # Block command while searching
    if is_searching():
        return {
            "success": False,
            "blocked": True,
            "message": "Friday is currently searching, please wait...",
        }

    if deduplicator.is_duplicate(command):
        return {"success": True, "duplicate": True, "message": "Duplicate command ignored"}

    if not state.is_powered_on:
        return {"success": False, "message": "FRIDAY is offline"}

    ai_result = ask_ai(command)
    speak_response = ai_result.get("speak_response", "")
    current_mode = get_ai_mode()

    # ── Command AI only — execute system commands ──
    if current_mode == "command" and ai_result.get("has_command") and ai_result.get("command"):
        mapped_command = ai_result["command"]
        logger.info("Command AI mapped '%s' → '%s'", command, mapped_command)
        if speak_response:
            speak(speak_response)
        executed = _execute_command_silent(mapped_command)
        return {
            "success": True,
            "executed": executed,
            "mapped": mapped_command,
            "response": speak_response,
            "aiMode": current_mode,
        }

    # ── General / Search AI — conversation only ──
    else:
        if speak_response:
            speak(speak_response)
        return {
            "success": True,
            "executed": False,
            "response": speak_response,
            "aiMode": current_mode,
        }


@router.get("/api/reminders")
async def list_reminders():
    return {"success": True, "items": reminder_store.list(include_done=False, limit=50)}


@router.post("/api/reminders")
async def create_reminder(data: ReminderCreate):
    try:
        due_at = datetime.fromisoformat(data.dueAt)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid dueAt ISO datetime")
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Empty title")
    r = reminder_store.create(title=title, due_at=due_at, repeat=data.repeat)
    state.push_alert(level="info", title="Reminder", message=f"Scheduled: {r.title}", ttl_seconds=15, meta={"reminderId": r.id})
    return {"success": True, "item": r.__dict__}


@router.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    ok = reminder_store.delete(reminder_id)
    return {"success": ok}


@router.post("/api/reminders/parse")
async def parse_and_create_reminder(data: Command):
    parsed = parse_reminder_text(data.text)
    if not parsed:
        raise HTTPException(status_code=400, detail="Could not parse reminder text")
    title, due = parsed
    r = reminder_store.create(title=title, due_at=due, repeat="none")
    state.push_alert(level="info", title="Reminder", message=f"Scheduled: {r.title}", ttl_seconds=15, meta={"reminderId": r.id})
    return {"success": True, "item": r.__dict__}


@router.get("/api/vision/status")
async def vision_status():
    return {
        "success": True,
        "airMouse": air_mouse.is_running(),
        "signLauncher": sign_launcher.is_running(),
    }


@router.post("/api/airmouse/start")
async def airmouse_start():
    ok, msg = air_mouse.start()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/api/airmouse/stop")
async def airmouse_stop():
    ok, msg = air_mouse.stop()
    return {"success": ok, "message": msg}


@router.post("/api/signlauncher/start")
async def signlauncher_start():
    ok, msg = sign_launcher.start()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/api/signlauncher/stop")
async def signlauncher_stop():
    ok, msg = sign_launcher.stop()
    return {"success": ok, "message": msg}


@router.get("/api/signlauncher/map")
async def signlauncher_map():
    return {"success": True, "mapping": sign_launcher.get_mapping()}


@router.post("/api/calendar/parse")
async def calendar_from_text(data: Command):
    ok = create_calendar_event_from_text(data.text)
    if not ok:
        raise HTTPException(status_code=400, detail="Could not parse calendar command")
    return {"success": True}


@router.post("/api/calendar/event")
async def calendar_create(data: CalendarCreate):
    try:
        start = datetime.fromisoformat(data.start)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start ISO datetime")
    ics_path = create_ics_event(
        title=data.title.strip() or "FRIDAY Event",
        start=start,
        duration_minutes=int(data.durationMinutes),
        description=data.description,
        location=data.location,
    )
    ok = open_in_windows_calendar(ics_path)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to open Windows Calendar import")
    return {"success": True}