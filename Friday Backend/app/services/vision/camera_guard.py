from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass
class CameraLease:
    owner: str


class CameraGuard:
    def __init__(self):
        self._lock = threading.Lock()
        self._lease: Optional[CameraLease] = None

    def acquire(self, owner: str) -> bool:
        with self._lock:
            if self._lease is not None:
                return False
            self._lease = CameraLease(owner=owner)
            return True

    def release(self, owner: str) -> None:
        with self._lock:
            if self._lease and self._lease.owner == owner:
                self._lease = None

    def current_owner(self) -> Optional[str]:
        with self._lock:
            return self._lease.owner if self._lease else None


camera_guard = CameraGuard()

