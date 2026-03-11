from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SystemState:
    """Manages the current state of the FRIDAY system."""
    def __init__(self):
        self.is_powered_on: bool = True
        self.is_speaking: bool = False
        self.is_mic_on: bool = True
        self.is_volume_on: bool = True
        self.last_command: str = ""
        self.awake: bool = False
        self.awake_until: datetime = None
        self.start_time: datetime = datetime.now()
        self.awake_duration: int = 30
        self.speak_func = None
        self.pending_action: str | None = None  # For follow-up clarification prompts
                                                 # e.g. after FRIDAY asks "Ano isesearch sir?"

    def is_awake(self) -> bool:
        if not self.awake:
            return False

        if self.awake_until and datetime.now() > self.awake_until:
            self.awake = False
            self.awake_until = None
            logger.info("FRIDAY went back to sleep (timeout)")
            if self.speak_func:
                self.speak_func("Sleep mode activated, sir. Say Friday to wake me.")
            return False

        return True

    def wake_up(self) -> None:
        self.awake = True
        self.awake_until = datetime.now() + timedelta(seconds=self.awake_duration)
        logger.info(f"FRIDAY is awake for {self.awake_duration} seconds")

    def extend_awake(self) -> None:
        if self.awake:
            self.awake_until = datetime.now() + timedelta(seconds=self.awake_duration)

    def sleep_now(self) -> None:
        self.awake = False
        self.awake_until = None
        logger.info("FRIDAY went to sleep")

    def reset(self):
        self.is_powered_on = True
        self.is_speaking = False
        self.is_mic_on = True
        self.is_volume_on = True
        self.last_command = ""
        self.awake = False
        self.pending_action = None  # Also clear pending action on reset


class CommandDeduplicator:
    """Prevents duplicate commands from being executed within a short time window."""
    def __init__(self):
        self.last_command: str = ""
        self.last_command_time: float = 0.0
        self.duplicate_window: float = 5.0

    def is_duplicate(self, command: str) -> bool:
        import time
        current_time = time.time()
        if (command == self.last_command and
                current_time - self.last_command_time < self.duplicate_window):
            logger.info(f"⏭️ Duplicate command blocked: '{command}' (within {self.duplicate_window}s)")
            return True

        self.last_command = command
        self.last_command_time = current_time
        return False


# Global instances
state = SystemState()
deduplicator = CommandDeduplicator()