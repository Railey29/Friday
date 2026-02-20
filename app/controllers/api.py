from fastapi import APIRouter, HTTPException, Request
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

    # Wake word
    if "friday" in command:
        state.wake_up()
        speak("Good day sir, pleasure to be at your service. How may I assist you today?")
        return {
            "success": True,
            "wake": True,
            "message": "Wake word detected",
            "awake_until": state.awake_until.isoformat() if state.awake_until else None,
        }

    # Sleep commands
    if any(phrase in command for phrase in ("go to sleep", "goodbye friday", "sleep friday")):
        if state.is_awake():
            state.sleep_now()
            speak("Of course, sir. Going into sleep mode. I'll be here when you need me.")
            return {"success": True, "sleep": True, "message": "FRIDAY is going to sleep"}

    # Execute with Gemini
    if state.is_awake():
        gemini_result = ask_gemini(command)
        speak_response = gemini_result.get("speak_response", "")

        if gemini_result.get("has_command") and gemini_result.get("command"):
            mapped_command = gemini_result["command"]
            logger.info("Gemini mapped '%s' → '%s'", command, mapped_command)

            # Speak Gemini's natural response first
            if speak_response:
                speak(speak_response)

            # Execute silently (no duplicate speak)
            executed = _execute_command_silent(mapped_command)
            if executed:
                state.extend_awake()

            return {
                "success": True,
                "executed": executed,
                "mapped": mapped_command,
                "response": speak_response,
                "awake_until": state.awake_until.isoformat() if state.awake_until else None,
            }
        else:
            # Gemini answered directly
            if speak_response:
                speak(speak_response)
            state.extend_awake()
            return {
                "success": True,
                "executed": False,
                "response": speak_response,
                "awake_until": state.awake_until.isoformat() if state.awake_until else None,
            }

    return {"success": True, "message": "Waiting for wake word ('Friday')"}