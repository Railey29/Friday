from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from app.models.state import state, deduplicator
from app.services.tts import speak
from app.services.stats import get_system_stats
from app.services.actions import execute_command, _execute_command_silent
from app.services.gemini_service import ask_gemini

import logging

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

    if deduplicator.is_duplicate(command):
        return {"success": True, "duplicate": True, "message": "Duplicate command ignored"}

    # FRIDAY is offline — only hard block
    if not state.is_powered_on:
        return {"success": False, "message": "FRIDAY is offline"}

    # ── Everything goes to Gemini — no wake word needed, no sleep mode ──
    gemini_result = ask_gemini(command)
    speak_response = gemini_result.get("speak_response", "")

    if gemini_result.get("has_command") and gemini_result.get("command"):
        mapped_command = gemini_result["command"]
        logger.info("Gemini mapped '%s' → '%s'", command, mapped_command)

        if speak_response:
            speak(speak_response)

        executed = _execute_command_silent(mapped_command)
        return {
            "success": True,
            "executed": executed,
            "mapped": mapped_command,
            "response": speak_response,
        }
    else:
        if speak_response:
            speak(speak_response)
        return {
            "success": True,
            "executed": False,
            "response": speak_response,
        }