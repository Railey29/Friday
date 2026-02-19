from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any

from app.models.state import state, deduplicator
from app.services.tts import speak
from app.services.stats import get_system_stats
from app.services.actions import execute_command  # ← single, correct import

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

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


@router.post("/api/speak")
async def speak_text(data: SpeakRequest):
    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")
    speak(data.text)
    return {"success": True, "text": data.text}


@router.post("/api/command")
async def receive_command(data: Command):
    command = data.text.lower().strip()
    logger.info("Received /api/command POST, command=%s", command)

    if not command:
        raise HTTPException(status_code=400, detail="Empty command")

    # ── Deduplication ──────────────────────────────────────────────────────────
    if deduplicator.is_duplicate(command):
        return {"success": True, "duplicate": True, "message": "Duplicate command ignored"}

    # ── Wake word ──────────────────────────────────────────────────────────────
    if "friday" in command:
        state.wake_up()
        speak("Good day sir, pleasure to be at your service. How may I assist you today?")
        return {
            "success": True,
            "wake": True,
            "message": "Wake word detected",
            "awake_until": state.awake_until.isoformat() if state.awake_until else None,
        }

    # ── Sleep commands ─────────────────────────────────────────────────────────
    if any(phrase in command for phrase in ("go to sleep", "goodbye friday", "sleep friday")):
        if state.is_awake():
            state.sleep_now()
            speak("Of course, sir. Going into sleep mode. I'll be here when you need me.")
            return {"success": True, "sleep": True, "message": "FRIDAY is going to sleep"}

    # ── Execute command (only when awake) ──────────────────────────────────────
    if state.is_awake():
        executed = execute_command(command)
        if executed:
            state.extend_awake()
        return {
            "success": True,
            "executed": executed,
            "message": "Command executed" if executed else "No matching command",
            "awake_until": state.awake_until.isoformat() if state.awake_until else None,
        }

    # ── Sleeping / waiting for wake word ──────────────────────────────────────
    return {"success": True, "message": "Waiting for wake word ('Friday')"}