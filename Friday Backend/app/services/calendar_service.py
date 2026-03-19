from __future__ import annotations

import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.models.state import state

logger = logging.getLogger(__name__)


def _format_ics_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def create_ics_event(
    *,
    title: str,
    start: datetime,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
) -> str:
    end = start + timedelta(minutes=max(1, int(duration_minutes)))
    uid = f"{uuid.uuid4().hex}@friday"
    dtstamp = _format_ics_dt(datetime.now())
    dtstart = _format_ics_dt(start)
    dtend = _format_ics_dt(end)

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FRIDAY//Voice Assistant//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{esc(title)}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{esc(description)}")
    if location:
        lines.append(f"LOCATION:{esc(location)}")
    lines += [
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]

    fd, path = tempfile.mkstemp(prefix="friday_event_", suffix=".ics", text=True)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return path


def open_in_windows_calendar(ics_path: str) -> bool:
    try:
        os.startfile(ics_path)
        return True
    except Exception as e:
        logger.warning("Failed to open calendar file: %s", e)
        return False


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
    "ng umaga": "am", "umaga": "am",
    "madaling araw": "am",
    "ng hapon": "pm", "hapon": "pm",
    "ng gabi": "pm", "gabi": "pm",
    "ng tanghali": "pm", "tanghali": "pm",
}

# Filipino calendar trigger keywords
_FIL_CALENDAR_TRIGGERS = (
    "add event", "create event", "add to calendar", "schedule", "calendar event",
    # Filipino
    "magdagdag ng event", "gumawa ng event",
    "idagdag sa kalendaryo", "idagdag sa calendar",
    "mag-schedule", "mag schedule",
    "i-schedule", "i schedule",
    "lagyan ng event",
    "itala sa kalendaryo",
)


def _normalize_filipino_time(text: str) -> str:
    """Convert Filipino time expressions to standard format."""
    t = text.lower()

    # ika-N ng <period>
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

    # alas/ala <word_number> [y medya] [ng <period>]
    m = re.search(
        r"\b(?:bandang\s+)?(?:alas?|ala)\s+([a-záéíóú ]+?)(?:\s+y\s+med[iy]a)?(?:\s+(?:ng\s+)?(?:umaga|hapon|gabi|tanghali|madaling araw))?\b",
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
                replacement, t, count=1,
            )
    return t


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


def _parse_date_base(text: str, *, base: datetime) -> Optional[datetime]:
    tl = text.lower()

    # Filipino
    if any(w in tl for w in ("bukas", "bukas na")):
        return datetime(base.year, base.month, base.day) + timedelta(days=1)
    if any(w in tl for w in ("ngayon", "ngayong araw")):
        return datetime(base.year, base.month, base.day)
    if "makalawa" in tl:
        return datetime(base.year, base.month, base.day) + timedelta(days=2)

    # English
    if "tomorrow" in tl:
        return datetime(base.year, base.month, base.day) + timedelta(days=1)
    if "today" in tl:
        return datetime(base.year, base.month, base.day)

    # ISO date
    m = re.search(r"\bon\s+(\d{4})-(\d{2})-(\d{2})\b", tl)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # English month: "on march 20"
    m = re.search(r"\bon\s+([a-zA-Z]+)\s+(\d{1,2})\b", tl)
    if m:
        month = _MONTHS.get(m.group(1).lower())
        if month:
            year = base.year
            candidate = datetime(year, month, int(m.group(2)))
            if candidate.date() < base.date():
                candidate = datetime(year + 1, month, int(m.group(2)))
            return candidate

    # Filipino month: "sa abril 5" / "ngayong marso 20"
    m = re.search(r"\b(?:sa|ngayong|ng)\s+([a-zA-Z]+)\s+(\d{1,2})\b", tl)
    if m:
        month = _MONTHS.get(m.group(1).lower())
        if month:
            year = base.year
            candidate = datetime(year, month, int(m.group(2)))
            if candidate.date() < base.date():
                candidate = datetime(year + 1, month, int(m.group(2)))
            return candidate

    return None


def _extract_event_title(text: str) -> str:
    """Extract event title from calendar command."""
    t = text.lower()

    # Remove trigger
    for trigger in sorted(_FIL_CALENDAR_TRIGGERS, key=len, reverse=True):
        if trigger in t:
            idx = t.index(trigger) + len(trigger)
            t = text[idx:].strip()
            break

    # Remove leading connectors
    t = re.sub(r"^(ng\s+|na\s+|para\s+sa\s+|ang\s+)", "", t, flags=re.IGNORECASE).strip()

    # Remove time/date trailing parts
    t = re.split(r"\b(?:at|ng|bukas|tomorrow|today|ngayon|sa|on|for)\b", t, flags=re.IGNORECASE)[0].strip()
    t = re.sub(r"\b(?:alas?|ala|ika)\b.*$", "", t, flags=re.IGNORECASE).strip()

    return t.title() if t else "FRIDAY Event"


def parse_calendar_text(text: str, *, now: Optional[datetime] = None) -> Optional[tuple[str, datetime, int]]:
    """
    Bilingual parser for calendar events.

    English examples:
      - "add event meeting on 2026-03-20 at 5pm"
      - "schedule dentist tomorrow at 10am for 30 minutes"
      - "add to calendar review on march 20 at 2pm"

    Filipino examples:
      - "mag-schedule ng meeting bukas ng alas singko ng hapon"
      - "idagdag sa calendar ang dentist bukas ng 10am"
      - "i-schedule ang review sa abril 20 ng 2pm for 30 minutes"
      - "gumawa ng event meeting ngayon ng alas dos ng hapon"
    """
    if not text:
        return None

    base = now or datetime.now()
    tl = text.lower()

    # Check trigger
    if not any(k in tl for k in _FIL_CALENDAR_TRIGGERS):
        return None

    # Normalize Filipino time
    tl_normalized = _normalize_filipino_time(tl)

    # Duration: "for 30 minutes" / "para sa 30 minuto"
    duration = 60
    m = re.search(
        r"\bfor\s+(\d+)\s*(minute|minutes|minuto|minutos|min|hour|hours|oras)\b",
        tl_normalized, re.IGNORECASE
    )
    if m:
        amount = int(m.group(1))
        unit = m.group(2).lower()
        duration = amount if any(unit.startswith(x) for x in ("min", "minu")) else amount * 60

    # Extract title
    title = _extract_event_title(text)

    # Parse time
    time_comp = _parse_time_component(tl_normalized)
    if not time_comp:
        return None

    # Parse date
    date_base = _parse_date_base(tl_normalized, base=base) or datetime(base.year, base.month, base.day)
    start = datetime(date_base.year, date_base.month, date_base.day, time_comp[0], time_comp[1])

    has_explicit_date = any(w in tl for w in ("bukas", "tomorrow", "ngayon", "today", "makalawa", "on "))
    if start <= base and not has_explicit_date:
        start = start + timedelta(days=1)

    return title, start, duration


def create_calendar_event_from_text(text: str) -> bool:
    parsed = parse_calendar_text(text)
    if not parsed:
        return False

    title, start, duration = parsed
    ics_path = create_ics_event(title=title, start=start, duration_minutes=duration)
    ok = open_in_windows_calendar(ics_path)
    if ok:
        state.push_alert(
            level="info",
            title="Calendar",
            message=f"Event created: {title} @ {start.strftime('%Y-%m-%d %H:%M')}",
            ttl_seconds=20,
        )
    else:
        state.push_alert(
            level="error",
            title="Calendar",
            message="Failed to open Windows Calendar import.",
            ttl_seconds=30,
        )
    return ok