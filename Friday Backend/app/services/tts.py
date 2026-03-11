import threading
import logging
import pyttsx3

from app.models.state import state

logger = logging.getLogger(__name__)


def speak(text: str) -> None:
    """Convert text to speech using pyttsx3 in a background thread."""
    if not state.is_powered_on or not state.is_volume_on:
        logger.info(f"[SPEAK] Muted/Offline - Message: {text}")
        return

    def run_tts():
        state.is_speaking = True
        logger.info(f"[FRIDAY]: {text}")
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", 170)
            voices = engine.getProperty("voices")
            if len(voices) > 1:
                engine.setProperty("voice", voices[1].id)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            logger.error(f"TTS Error: {e}")
        finally:
            state.is_speaking = False

    threading.Thread(target=run_tts, daemon=True).start()


# expose speak for other modules and register it on state
state.speak_func = speak
