from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.models.state import state
from app.services.tts import speak

logger = logging.getLogger(__name__)


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REMINDERS_PATH = DATA_DIR / "reminders.json"


@dataclass(frozen=True)
class Reminder:
    id: str
    title: str
    dueAt: str
    createdAt: str
    repeat: str = "none"  # none|daily|weekly
    done: bool = False

    @staticmethod
    def from_dict(d: dict) -> "Reminder":
        return Reminder(
            id=str(d.get("id") or uuid.uuid4().hex),
            title=str(d.get("title") or ""),
            dueAt=str(d.get("dueAt") or datetime.now().isoformat()),
            createdAt=str(d.get("createdAt") or datetime.now().isoformat()),
            repeat=str(d.get("repeat") or "none"),
            done=bool(d.get("done") or False),
        )


class ReminderStore:
    def __init__(self, path: Path = REMINDERS_PATH):
        self._path = path
        self._lock = threading.Lock()
        self._items: list[Reminder] = []
        self._load()

    def _load(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._items = []
                return
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                self._items = [Reminder.from_dict(x) for x in raw]
            else:
                self._items = []
        except Exception as e:
            logger.warning("Failed to load reminders: %s", e)
            self._items = []

    def _save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = [asdict(r) for r in self._items]
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def list(self, *, include_done: bool = False, limit: int = 50) -> list[dict]:
        with self._lock:
            items = self._items[:]
        if not include_done:
            items = [r for r in items if not r.done]
        items.sort(key=lambda r: r.dueAt)
        return [asdict(r) for r in items[:limit]]

    def get(self, reminder_id: str) -> Optional[Reminder]:
        with self._lock:
            for r in self._items:
                if r.id == reminder_id:
                    return r
        return None

    def upsert(self, reminder: Reminder) -> None:
        with self._lock:
            replaced = False
            new_items: list[Reminder] = []
            for r in self._items:
                if r.id == reminder.id:
                    new_items.append(reminder)
                    replaced = True
                else:
                    new_items.append(r)
            if not replaced:
                new_items.append(reminder)
            self._items = new_items
            self._save()

    def create(self, *, title: str, due_at: datetime, repeat: str = "none") -> Reminder:
        reminder = Reminder(
            id=uuid.uuid4().hex,
            title=title.strip(),
            dueAt=due_at.isoformat(),
            createdAt=datetime.now().isoformat(),
            repeat=repeat,
            done=False,
        )
        with self._lock:
            self._items.append(reminder)
            self._save()
        return reminder

    def delete(self, reminder_id: str) -> bool:
        with self._lock:
            before = len(self._items)
            self._items = [r for r in self._items if r.id != reminder_id]
            changed = len(self._items) != before
            if changed:
                self._save()
            return changed

    def mark_done(self, reminder_id: str, done: bool = True) -> bool:
        reminder = self.get(reminder_id)
        if reminder is None:
            return False
        self.upsert(Reminder(**{**asdict(reminder), "done": done}))
        return True

    def snooze(self, reminder_id: str, minutes: int) -> bool:
        reminder = self.get(reminder_id)
        if reminder is None:
            return False
        try:
            due_at = datetime.fromisoformat(reminder.dueAt)
        except Exception:
            due_at = datetime.now()
        due_at = max(datetime.now(), due_at) + timedelta(minutes=max(1, minutes))
        self.upsert(Reminder(**{**asdict(reminder), "dueAt": due_at.isoformat()}))
        return True


def _parse_time_component(text: str) -> Optional[tuple[int, int]]:
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text, re.IGNORECASE)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or "0")
    ampm = (m.group(3) or "").lower()
    if ampm:
        if hour == 12:
            hour = 0
        if ampm == "pm":
            hour += 12
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour, minute


_MONTHS = {
    # English
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
    # Filipino
    "enero": 1,
    "pebrero": 2,
    "marso": 3,
    "abril": 4,
    "mayo": 5,
    "hunyo": 6,
    "hulyo": 7,
    "agosto": 8,
    "setyembre": 9, "septiyembre": 9,
    "oktubre": 10,
    "nobyembre": 11,
    "disyembre": 12,
}

# ─────────────────────────────────────────────
# Filipino time normalizer
# Converts Filipino time expressions to standard format
# e.g. "alas singko ng hapon" → "5pm"
#      "alas otso ng umaga"   → "8am"
# ─────────────────────────────────────────────

_FILIPINO_NUMBERS = {
    "una": 1, "isa": 1,
    "dos": 2, "dalawa": 2,
    "tres": 3, "tatlo": 3,
    "quatro": 4, "kwatro": 4, "apat": 4,
    "singko": 5, "lima": 5,
    "sais": 6, "anim": 6,
    "syete": 7, "pito": 7,
    "otso": 8, "walo": 8,
    "nuwebe": 9, "siyam": 9,
    "diyes": 10, "sampu": 10,
    "onse": 11, "labing isa": 11,
    "dose": 12, "labindalawa": 12,
}

_FILIPINO_PERIOD = {
    # morning
    "ng umaga": "am", "umaga": "am",
    "madaling araw": "am",
    # afternoon
    "ng hapon": "pm", "hapon": "pm",
    # evening
    "ng gabi": "pm", "gabi": "pm",
    "ng tanghali": "pm", "tanghali": "pm",
}


def _normalize_filipino_time(text: str) -> str:
    """
    Converts Filipino time expressions into English-style time strings
    so the standard _parse_time_component can handle them.

    Examples:
      "alas singko ng hapon"    → "5pm"
      "alas otso ng umaga"      → "8am"
      "alas dose ng tanghali"   → "12pm"
      "bandang alas tres"       → "3"
      "ika-7 ng gabi"           → "7pm"
      "alas dose y medya"       → "12:30"
    """
    t = text.lower()

    # ── ika-N ng <period> ──────────────────────────────────────
    m = re.search(r"\bika[-\s]?(\d{1,2})\b", t)
    if m:
        hour = int(m.group(1))
        period = ""
        for key, val in _FILIPINO_PERIOD.items():
            if key in t:
                period = val
                break
        t = re.sub(r"\bika[-\s]?\d{1,2}\b", f"{hour}{period}", t)
        return t

    # ── alas/ala <word_number> [y medya] [ng <period>] ────────
    m = re.search(
        r"\b(?:bandang\s+)?(?:alas?|ala)\s+([a-záéíóú ]+?)(?:\s+y\s+medya)?(?:\s+(?:ng\s+)?(?:umaga|hapon|gabi|tanghali|madaling araw))?\b",
        t,
    )
    if m:
        num_word = m.group(1).strip()
        hour = _FILIPINO_NUMBERS.get(num_word)
        if hour:
            half = "y medya" in t or "y media" in t
            minute_str = ":30" if half else ""
            period = ""
            for key, val in _FILIPINO_PERIOD.items():
                if key in t:
                    period = val
                    break
            replacement = f"{hour}{minute_str}{period}"
            t = re.sub(
                r"\b(?:bandang\s+)?(?:alas?|ala)\s+[a-záéíóú ]+?(?:\s+y\s+med[iy]a)?(?:\s+(?:ng\s+)?(?:umaga|hapon|gabi|tanghali|madaling araw))?\b",
                replacement,
                t,
                count=1,
            )
    return t


def _parse_date_component(text: str, *, base: datetime) -> Optional[datetime]:
    t = text.lower()

    # Filipino date words
    if any(w in t for w in ("bukas", "bukas na")):
        return datetime(base.year, base.month, base.day) + timedelta(days=1)
    if any(w in t for w in ("ngayon", "ngayong araw")):
        return datetime(base.year, base.month, base.day)
    if "makalawa" in t:
        return datetime(base.year, base.month, base.day) + timedelta(days=2)

    # English date words
    if "tomorrow" in t:
        return datetime(base.year, base.month, base.day) + timedelta(days=1)
    if "today" in t:
        return datetime(base.year, base.month, base.day)

    # ISO date: "on 2026-03-20"
    m = re.search(r"\bon\s+(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # English month name: "on march 20"
    m = re.search(r"\bon\s+([a-zA-Z]+)\s+(\d{1,2})\b", t)
    if m:
        month_name = m.group(1).lower()
        day = int(m.group(2))
        month = _MONTHS.get(month_name)
        if month:
            year = base.year
            candidate = datetime(year, month, day)
            if candidate.date() < base.date():
                candidate = datetime(year + 1, month, day)
            return candidate

    # Filipino month name: "sa marso 20" / "ngayong abril 5"
    m = re.search(r"\b(?:sa|ngayong|ng)\s+([a-zA-Z]+)\s+(\d{1,2})\b", t)
    if m:
        month_name = m.group(1).lower()
        day = int(m.group(2))
        month = _MONTHS.get(month_name)
        if month:
            year = base.year
            candidate = datetime(year, month, day)
            if candidate.date() < base.date():
                candidate = datetime(year + 1, month, day)
            return candidate

    return None


# ─────────────────────────────────────────────
# Filipino trigger keywords
# ─────────────────────────────────────────────

_FIL_REMINDER_TRIGGERS = (
    "ipaalala mo",
    "ipaalala",
    "magpaalaala",
    "remind me",
    "set a reminder",
    "set reminder",
    "mag-reminder",
    "mag reminder",
    "paalalahanan mo ako",
    "huwag akong palampasin",
)

_FIL_IN_KEYWORDS = (
    # English
    " in ",
    # Filipino
    " pagkatapos ng ",
    " pagkatapos ",
    " after ",
    " makalipas ng ",
)

_FIL_AT_KEYWORDS = (
    # English
    " at ",
    # Filipino
    " ng ",
    " nang ",
    " bandang ",
    " sa ",
)

_FIL_MINUTE_WORDS = (
    "minute", "minutes", "min",
    "minuto", "minutos",
)

_FIL_HOUR_WORDS = (
    "hour", "hours",
    "oras",
)


def parse_reminder_text(text: str, *, now: Optional[datetime] = None) -> Optional[tuple[str, datetime]]:
    """
    Bilingual parser for reminders — supports English and Filipino.

    English examples:
      - "remind me to take medicine in 10 minutes"
      - "remind me to call mom at 5pm tomorrow"
      - "set a reminder to submit report at 9am on march 20"

    Filipino examples:
      - "ipaalala mo na mag-inom ng gamot pagkatapos ng 10 minuto"
      - "ipaalala mo na tumawag kay mama bukas ng alas singko ng hapon"
      - "mag-reminder na mag-aral bukas ng 8pm"
      - "paalalahanan mo ako na mag-exercise ngayon ng alas otso ng gabi"
      - "ipaalala mo na kumain ng tanghalian sa tanghali"
    """
    if not text:
        return None

    base = now or datetime.now()
    t = text.strip()
    tl = t.lower()

    # ── Check if it's a reminder command ──────────────────────
    has_trigger = any(trigger in tl for trigger in _FIL_REMINDER_TRIGGERS)
    if not has_trigger:
        return None

    # ── Normalize Filipino time expressions first ──────────────
    tl_normalized = _normalize_filipino_time(tl)

    # ── Try "in X minutes/hours" pattern ──────────────────────
    # English: "in 10 minutes" / Filipino: "pagkatapos ng 10 minuto"
    m = re.search(
        r"\b(?:in|pagkatapos\s+ng|pagkatapos|makalipas\s+ng)\s+(\d+)\s*("
        + "|".join(_FIL_MINUTE_WORDS + _FIL_HOUR_WORDS)
        + r")\b",
        tl_normalized,
        re.IGNORECASE,
    )
    if m:
        # Extract title — everything after trigger, before time expression
        title = _extract_title_filipino(tl, tl_normalized, trigger_end=True)
        amount = int(m.group(1))
        unit = m.group(2).lower()
        is_hour = any(unit.startswith(h) for h in ("hour", "oras"))
        due = base + (timedelta(hours=amount) if is_hour else timedelta(minutes=amount))
        return title or "Reminder", due

    # ── Try "at <time>" pattern ────────────────────────────────
    # Works for both English ("at 5pm") and normalized Filipino ("5pm", "8am")
    m = re.search(
        r"\b(?:at|ng|nang|bandang|sa)\s+(\d{1,2}(?::\d{2})?(?:am|pm)?)\b",
        tl_normalized,
        re.IGNORECASE,
    )
    if m:
        title = _extract_title_filipino(tl, tl_normalized, trigger_end=True)
        trailing = tl_normalized[m.start():]
        time_comp = _parse_time_component(trailing)
        if not time_comp:
            return None
        date_base = _parse_date_component(tl_normalized, base=base) or datetime(base.year, base.month, base.day)
        due = datetime(date_base.year, date_base.month, date_base.day, time_comp[0], time_comp[1])

        # If time already passed today and no explicit date given, push to tomorrow
        has_explicit_date = any(w in tl for w in ("bukas", "tomorrow", "ngayon", "today", "makalawa", "on "))
        if due <= base and not has_explicit_date:
            due = due + timedelta(days=1)

        return title or "Reminder", due

    return None


def _extract_title_filipino(original: str, normalized: str, *, trigger_end: bool = True) -> str:
    """
    Extracts the task title from a reminder command by removing
    the trigger phrase and time expressions.
    """
    t = original.lower()

    # Remove trigger phrase
    for trigger in sorted(_FIL_REMINDER_TRIGGERS, key=len, reverse=True):
        if trigger in t:
            t = t[t.index(trigger) + len(trigger):].strip()
            break

    # Remove leading connectors: "na", "to", "na mag-", "na i-"
    t = re.sub(r"^(na\s+|to\s+|ng\s+)", "", t).strip()

    # Remove time/date trailing fragments
    t = re.sub(
        r"\b(?:in|pagkatapos\s+ng?|makalipas\s+ng?)\s+\d+\s*(?:minuto|minutos|minute|minutes|min|oras|hour|hours)\b.*$",
        "", t, flags=re.IGNORECASE
    ).strip()
    t = re.sub(
        r"\b(?:at|ng|nang|bandang|sa)\s+\d{1,2}(?::\d{2})?(?:am|pm)?\b.*$",
        "", t, flags=re.IGNORECASE
    ).strip()
    t = re.sub(
        r"\b(?:bukas|tomorrow|ngayon|today|makalawa|after tomorrow)\b.*$",
        "", t, flags=re.IGNORECASE
    ).strip()
    t = re.sub(
        r"\b(?:alas?|ala)\s+[a-z]+.*$",
        "", t, flags=re.IGNORECASE
    ).strip()

    # Capitalize first letter
    return t.capitalize() if t else "Reminder"


class ReminderScheduler:
    def __init__(self, store: ReminderStore):
        self._store = store
        self._task: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._task and self._task.is_alive():
            return
        self._stop.clear()
        self._task = threading.Thread(target=self._run, daemon=True)
        self._task.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
                state.prune_alerts()
            except Exception as e:
                logger.warning("ReminderScheduler tick failed: %s", e)
            self._stop.wait(1.0)

    def tick(self) -> None:
        now = datetime.now()
        due_items: list[Reminder] = []
        for raw in self._store.list(include_done=False, limit=200):
            r = Reminder.from_dict(raw)
            try:
                due_at = datetime.fromisoformat(r.dueAt)
                due_at_naive = due_at.replace(tzinfo=None)  # ← FIX
            except Exception:
                continue
            if due_at_naive <= now:  # ← FIX
                due_items.append(r)

        for r in due_items:
            self._trigger(r, now=now)

    def _trigger(self, reminder: Reminder, *, now: datetime) -> None:
        logger.info("Reminder due: %s (%s)", reminder.title, reminder.id)
        state.push_alert(
            level="reminder",
            title="Task Reminder",
            message=reminder.title,
            ttl_seconds=60,
            meta={"reminderId": reminder.id},
        )
        speak(f"Paalala po, sir. {reminder.title}")

        repeat = (reminder.repeat or "none").lower()
        if repeat == "daily":
            next_due = now + timedelta(days=1)
            self._store.upsert(Reminder(**{**asdict(reminder), "dueAt": next_due.isoformat()}))
        elif repeat == "weekly":
            next_due = now + timedelta(days=7)
            self._store.upsert(Reminder(**{**asdict(reminder), "dueAt": next_due.isoformat()}))
        else:
            self._store.mark_done(reminder.id, True)


store = ReminderStore()
scheduler = ReminderScheduler(store)