from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging

from app.models.state import state, deduplicator
from app.services.stats import get_system_stats
from app.services.actions import execute_command
from app.services.tts import speak
from app.services.ai_router import ask_ai, get_ai_mode, is_searching
from app.services.reminders import store as reminder_store
from app.services.vision.air_mouse import air_mouse
from app.services.vision.sign_launcher import sign_launcher

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def sender():
        try:
            while True:
                state.prune_alerts()
                await websocket.send_json({
                    "isPoweredOn": state.is_powered_on,
                    "isSpeaking": state.is_speaking,
                    "isMicOn": state.is_mic_on,
                    "isVolumeOn": state.is_volume_on,
                    "lastCommand": state.last_command,
                    "awake": state.is_awake(),
                    "awakeUntil": state.awake_until.isoformat() if state.awake_until else None,
                    "stats": get_system_stats(),
                    "alerts": state.alerts,
                    "reminders": reminder_store.list(include_done=False, limit=20),
                    "vision": {
                        "airMouse": air_mouse.is_running(),
                        "signLauncher": sign_launcher.is_running(),
                    },
                    "aiMode": get_ai_mode(),
                    "isSearching": is_searching(),  # ← send search lock state
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

                cmd_text = payload.get("text")
                if not cmd_text:
                    continue

                command = str(cmd_text).lower().strip()
                logger.info("ws: received command=%s ai_mode=%s is_searching=%s",
                            command, get_ai_mode(), is_searching())

                if not command:
                    await websocket.send_json({"success": False, "error": "Empty command"})
                    continue

                # ── Search Lock — block commands while searching ──
                if is_searching():
                    logger.info("ws: command blocked — Friday is currently searching")
                    await websocket.send_json({
                        "success": False,
                        "blocked": True,
                        "message": "Friday is currently searching, please wait...",
                        "isSearching": True,
                    })
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
                    # ── Route to selected AI brain ──
                    loop = asyncio.get_event_loop()
                    ai_result = await loop.run_in_executor(None, ask_ai, command)

                    current_mode = get_ai_mode()
                    speak_response = ai_result.get("speak_response", "")

                    # ── Command AI — execute system commands ──
                    if current_mode == "command" and ai_result.get("has_command") and ai_result.get("command"):
                        mapped_command = ai_result["command"]
                        logger.info("Command AI mapped '%s' → '%s'", command, mapped_command)

                        if speak_response:
                            speak(speak_response)

                        executed = execute_command(mapped_command)
                        if executed:
                            state.extend_awake()

                        await websocket.send_json({
                            "success": True,
                            "executed": executed,
                            "mapped": mapped_command,
                            "aiMode": current_mode,
                            "isSearching": False,
                        })

                    # ── General / Search AI — conversation only, no commands ──
                    else:
                        friday_response = speak_response or ai_result.get(
                            "friday_response",
                            "I'm not sure how to help with that, sir."
                        )
                        if friday_response:
                            speak(friday_response)
                        state.extend_awake()

                        await websocket.send_json({
                            "success": True,
                            "executed": False,
                            "response": friday_response,
                            "aiMode": current_mode,
                            "isSearching": False,
                            "mode": ai_result.get("mode", current_mode),
                        })
                else:
                    await websocket.send_json({
                        "success": True,
                        "message": "Waiting for wake word ('Friday')"
                    })

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