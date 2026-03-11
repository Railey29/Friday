from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging

from app.models.state import state, deduplicator
from app.services.stats import get_system_stats
from app.services.actions import execute_command
from app.services.tts import speak
from app.services.gemini_service import ask_gemini  # ← ADDED

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def sender():
        try:
            while True:
                await websocket.send_json({
                    "isPoweredOn": state.is_powered_on,
                    "isSpeaking": state.is_speaking,
                    "isMicOn": state.is_mic_on,
                    "isVolumeOn": state.is_volume_on,
                    "lastCommand": state.last_command,
                    "awake": state.is_awake(),
                    "awakeUntil": state.awake_until.isoformat() if state.awake_until else None,
                    "stats": get_system_stats(),
                })
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            raise

    async def receiver():
        try:
            while True:
                text = await websocket.receive_text()
                try:
                    payload = json.loads(text)
                except Exception:
                    logger.warning("ws: received non-json payload: %s", text)
                    continue

                # Expecting { "text": "..." }
                cmd_text = payload.get("text")
                if not cmd_text:
                    continue

                command = str(cmd_text).lower().strip()
                logger.info("ws: received command=%s", command)

                if not command:
                    await websocket.send_json({"success": False, "error": "Empty command"})
                    continue

                if deduplicator.is_duplicate(command):
                    await websocket.send_json({"success": True, "duplicate": True})
                    continue

                if "friday" in command:
                    state.wake_up()
                    speak("Good day sir, pleasure to be at your service. How may I assist you today?")
                    await websocket.send_json({"success": True, "wake": True})
                    continue

                if state.is_awake():
                    # ── GEMINI INTEGRATION START ──
                    loop = asyncio.get_event_loop()
                    gemini_result = await loop.run_in_executor(None, ask_gemini, command)

                    if gemini_result.get("has_command") and gemini_result.get("command"):
                        # Gemini found a matching FRIDAY command
                        mapped_command = gemini_result["command"]
                        logger.info("Gemini mapped '%s' → '%s'", command, mapped_command)
                        executed = execute_command(mapped_command)
                        if executed:
                            state.extend_awake()
                        await websocket.send_json({
                            "success": True,
                            "executed": executed,
                            "mapped": mapped_command
                        })
                    else:
                        # Gemini answered directly (tanong, chika, walang match na command)
                        friday_response = gemini_result.get(
                            "friday_response",
                            "I'm not sure how to help with that, sir."
                        )
                        speak(friday_response)
                        state.extend_awake()
                        await websocket.send_json({
                            "success": True,
                            "executed": False,
                            "response": friday_response
                        })
                    # ── GEMINI INTEGRATION END ──

                else:
                    await websocket.send_json({"success": True, "message": "Waiting for wake word ('Friday')"})

        except WebSocketDisconnect:
            raise

    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        await asyncio.gather(sender_task, receiver_task)
    except WebSocketDisconnect:
        sender_task.cancel()
        receiver_task.cancel()
        return
    except Exception:
        sender_task.cancel()
        receiver_task.cancel()
        return