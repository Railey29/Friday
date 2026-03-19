from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.models.state import state

from .camera_guard import camera_guard

logger = logging.getLogger(__name__)

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

try:
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover
    mp = None


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAP_PATH = DATA_DIR / "sign_launcher_map.json"


DEFAULT_MAP = {
    "OPEN_PALM":     "show desktop",
    "FIST":          "close window",
    "PEACE":         "open browser",
    "POINT":         "open file explorer",
    "CALL_SIGN":     "open meet",
    "THREE_FINGERS": "screenshot",
}


@dataclass
class SignLauncherConfig:
    camera_index: int = 0
    cooldown_sec: float = 1.5   # balanced — not too slow, not too fast
    stable_frames: int = 8      # balanced — accurate but responsive


def _load_map() -> dict:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not MAP_PATH.exists():
            MAP_PATH.write_text(json.dumps(DEFAULT_MAP, indent=2), encoding="utf-8")
            return dict(DEFAULT_MAP)
        raw = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
    except Exception as e:
        logger.warning("Failed to load sign map: %s", e)
    return dict(DEFAULT_MAP)


def _classify_gesture(landmarks) -> str:
    """
    Classify hand gesture from MediaPipe landmarks.

    Finger landmarks:
      Thumb:  tip=4, ip=3, mcp=2
      Index:  tip=8, pip=6
      Middle: tip=12, pip=10
      Ring:   tip=16, pip=14
      Pinky:  tip=20, pip=18
    """

    def extended(tip: int, pip: int) -> bool:
        return landmarks[tip].y < landmarks[pip].y

    index  = extended(8, 6)
    middle = extended(12, 10)
    ring   = extended(16, 14)
    pinky  = extended(20, 18)

    # Thumb: horizontal distance from tip to MCP
    thumb = abs(landmarks[4].x - landmarks[2].x) > 0.08

    fingers = (thumb, index, middle, ring, pinky)

    # ── FIST — all fingers folded ──────────────────────────────
    if fingers == (False, False, False, False, False):
        return "FIST"

    # ── OPEN PALM — all fingers extended ──────────────────────
    if fingers == (True, True, True, True, True):
        return "OPEN_PALM"

    # ── PEACE — index + middle only ───────────────────────────
    if fingers[1:] == (True, True, False, False):
        return "PEACE"

    # ── POINT — index only ────────────────────────────────────
    if fingers == (False, True, False, False, False):
        return "POINT"

    # ── THREE FINGERS — index + middle + ring ─────────────────
    if fingers[1:] == (True, True, True, False):
        return "THREE_FINGERS"

    # ── CALL SIGN — thumb + pinky extended, rest folded ───────
    thumb_ext = landmarks[4].y < landmarks[3].y   # thumb tip above thumb IP
    pinky_ext = extended(20, 18)
    index_fold  = not extended(8, 6)
    middle_fold = not extended(12, 10)
    ring_fold   = not extended(16, 14)
    if thumb_ext and pinky_ext and index_fold and middle_fold and ring_fold:
        return "CALL_SIGN"

    return "UNKNOWN"


class SignLauncherService:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._config = SignLauncherConfig()
        self._map = _load_map()

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self, config: Optional[SignLauncherConfig] = None) -> tuple[bool, str]:
        if self.is_running():
            return True, "Sign Launcher already running"
        if cv2 is None or mp is None:
            return False, "Missing dependencies. Install: opencv-python, mediapipe"
        if not camera_guard.acquire("sign_launcher"):
            owner = camera_guard.current_owner()
            return False, f"Camera is currently in use by: {owner}"

        self._map = _load_map()
        self._config = config or self._config
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        state.push_alert(
            level="info",
            title="Sign Launcher",
            message="Sign Launcher started — show a gesture!",
            ttl_seconds=10,
        )
        return True, "started"

    def stop(self) -> tuple[bool, str]:
        if not self.is_running():
            camera_guard.release("sign_launcher")
            return True, "Sign Launcher not running"
        self._stop.set()
        state.push_alert(level="info", title="Sign Launcher", message="Stopping…", ttl_seconds=10)
        return True, "stopping"

    def get_mapping(self) -> dict:
        return dict(self._map)

    def update_mapping(self, mapping: dict) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._map = {str(k): str(v) for k, v in mapping.items()}
        MAP_PATH.write_text(json.dumps(self._map, indent=2), encoding="utf-8")

    def _run(self) -> None:
        self._running = True
        last_trigger = 0.0
        last_gesture = None
        stable = 0
        try:
            cap = cv2.VideoCapture(self._config.camera_index)
            if not cap.isOpened():
                state.push_alert(level="error", title="Sign Launcher", message="Failed to open camera", ttl_seconds=20)
                return

            hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.6,   # slightly higher = more accurate
                min_tracking_confidence=0.6,
            )

            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = hands.process(rgb)

                if not res.multi_hand_landmarks:
                    stable = 0
                    last_gesture = None
                    continue

                lm = res.multi_hand_landmarks[0].landmark
                gesture = _classify_gesture(lm)

                # Ignore UNKNOWN — don't let it reset stable streak
                if gesture == "UNKNOWN":
                    continue

                if gesture == last_gesture:
                    stable += 1
                else:
                    stable = 1
                    last_gesture = gesture

                if stable < int(self._config.stable_frames):
                    continue

                now = time.time()
                if (now - last_trigger) < float(self._config.cooldown_sec):
                    continue

                cmd = self._map.get(gesture)
                if cmd:
                    last_trigger = now
                    self._trigger_command(gesture, cmd)

        except Exception as e:
            logger.warning("SignLauncher crashed: %s", e)
            state.push_alert(level="error", title="Sign Launcher", message=str(e), ttl_seconds=30)
        finally:
            try:
                cap.release()
                camera_guard.release("sign_launcher")
            except Exception:
                pass
            self._running = False
            state.push_alert(level="info", title="Sign Launcher", message="Sign Launcher stopped", ttl_seconds=10)

    def _trigger_command(self, gesture: str, cmd: str) -> None:
        state.push_alert(level="info", title="Sign Launcher", message=f"{gesture} → {cmd}", ttl_seconds=8)
        try:
            from app.services.actions import execute_command
            threading.Thread(target=lambda: execute_command(cmd), daemon=True).start()
        except Exception as e:
            state.push_alert(level="error", title="Sign Launcher", message=str(e), ttl_seconds=15)


sign_launcher = SignLauncherService()