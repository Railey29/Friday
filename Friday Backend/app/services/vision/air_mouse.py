from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass
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

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover
    pyautogui = None


@dataclass
class AirMouseConfig:
    camera_index: int = 0
    smoothing: float = 0.25  # 0..1, higher = more smoothing
    click_pinch_threshold: float = 0.045  # normalized landmark distance
    click_cooldown_sec: float = 0.6
    fist_threshold: float = 0.08        # max fingertip-to-palm dist to count as fist
    fist_confirm_sec: float = 1.5       # hold fist this long to stop


def _is_fist(lm, threshold: float) -> bool:
    """
    Returns True when all four finger tips are close to the palm center.
    Fingertips: index=8, middle=12, ring=16, pinky=20
    Palm center approximated by wrist(0) + middle MCP(9) midpoint.
    """
    palm_x = (lm[0].x + lm[9].x) / 2
    palm_y = (lm[0].y + lm[9].y) / 2
    tips = [8, 12, 16, 20]
    for tip in tips:
        dist = math.hypot(lm[tip].x - palm_x, lm[tip].y - palm_y)
        if dist > threshold:
            return False
    return True


class AirMouseService:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._config = AirMouseConfig()

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self, config: Optional[AirMouseConfig] = None) -> tuple[bool, str]:
        if self.is_running():
            return True, "Air Mouse already running"
        if cv2 is None or mp is None or pyautogui is None:
            return False, "Missing dependencies. Install: opencv-python, mediapipe, pyautogui"
        if not camera_guard.acquire("air_mouse"):
            owner = camera_guard.current_owner()
            return False, f"Camera is currently in use by: {owner}"

        self._config = config or self._config
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        state.push_alert(level="info", title="Air Mouse", message="Air Mouse started — ✊ Hold fist to stop", ttl_seconds=10)
        return True, "started"

    def stop(self) -> tuple[bool, str]:
        if not self.is_running():
            camera_guard.release("air_mouse")
            return True, "Air Mouse not running"
        self._stop.set()
        state.push_alert(level="info", title="Air Mouse", message="Stopping…", ttl_seconds=10)
        return True, "stopping"

    def _run(self) -> None:
        self._running = True
        try:
            pyautogui.FAILSAFE = False
            screen_w, screen_h = pyautogui.size()

            cap = cv2.VideoCapture(self._config.camera_index)
            if not cap.isOpened():
                state.push_alert(level="error", title="Air Mouse", message="Failed to open camera", ttl_seconds=20)
                return

            hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

            last_x = None
            last_y = None
            last_click = 0.0
            fist_since: Optional[float] = None  # timestamp when fist started

            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = hands.process(rgb)

                if not res.multi_hand_landmarks:
                    fist_since = None  # reset if no hand detected
                    continue

                lm = res.multi_hand_landmarks[0].landmark

                # ── FIST DETECTION (stop gesture) ──────────────────────────
                if _is_fist(lm, self._config.fist_threshold):
                    if fist_since is None:
                        fist_since = time.time()
                        state.push_alert(level="info", title="Air Mouse", message="✊ Hold fist to stop...", ttl_seconds=3)
                    elif (time.time() - fist_since) >= self._config.fist_confirm_sec:
                        state.push_alert(level="info", title="Air Mouse", message="✊ Fist detected — stopping Air Mouse", ttl_seconds=5)
                        self._stop.set()
                        break
                    continue  # don't move mouse while fist is held
                else:
                    fist_since = None  # reset if fist released

                # ── CURSOR MOVEMENT ────────────────────────────────────────
                # index fingertip (8) controls cursor
                idx = lm[8]
                x = idx.x * screen_w
                y = idx.y * screen_h

                if last_x is None or last_y is None:
                    smooth_x, smooth_y = x, y
                else:
                    a = float(self._config.smoothing)
                    smooth_x = last_x + (x - last_x) * (1.0 - a)
                    smooth_y = last_y + (y - last_y) * (1.0 - a)

                pyautogui.moveTo(smooth_x, smooth_y, _pause=False)
                last_x, last_y = smooth_x, smooth_y

                # ── PINCH CLICK ────────────────────────────────────────────
                # thumb tip (4) vs index tip (8)
                thumb = lm[4]
                pinch = math.hypot(thumb.x - idx.x, thumb.y - idx.y)
                now = time.time()
                if pinch < self._config.click_pinch_threshold and (now - last_click) > self._config.click_cooldown_sec:
                    pyautogui.click()
                    last_click = now

        except Exception as e:
            logger.warning("AirMouse crashed: %s", e)
            state.push_alert(level="error", title="Air Mouse", message=str(e), ttl_seconds=30)
        finally:
            try:
                cap.release()
                camera_guard.release("air_mouse")
            except Exception:
                pass
            self._running = False
            state.push_alert(level="info", title="Air Mouse", message="Air Mouse stopped", ttl_seconds=10)


air_mouse = AirMouseService()