"""Утилиты форматирования дат, телефонов, HTML."""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from config import TIMEZONE


def tz() -> ZoneInfo:
    return ZoneInfo(TIMEZONE)


def now_local() -> datetime:
    return datetime.now(tz=tz())


def format_date(d) -> str:
    """'15 января 2025 (среда)'"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    months = ["","января","февраля","марта","апреля","мая","июня",
              "июля","августа","сентября","октября","ноября","декабря"]
    weekdays = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]
    return f"{d.day} {months[d.month]} {d.year} ({weekdays[d.weekday()]})"


def format_date_short(d) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return d.strftime("%d.%m.%Y")


def format_time(t: str) -> str:
    return t


def validate_phone(phone: str) -> str | None:
    digits = re.sub(r"[^\d]", "", phone)
    if len(digits) < 10:
        return None
    if digits.startswith("7") and len(digits) == 11:
        return f"+{digits}"
    if digits.startswith("8") and len(digits) == 11:
        return f"+7{digits[1:]}"
    if len(digits) == 10:
        return f"+7{digits}"
    return f"+{digits}" if len(digits) >= 10 else None


def validate_time(t: str) -> bool:
    return bool(re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", t.strip()))


def escape_html(text: str) -> str:
    return str(text).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


def format_comment(c: str | None) -> str:
    return escape_html(c.strip()) if c and c.strip() else "не указан"


def estimate_eta_seconds(track_count: int, delay: float = 0.3) -> str:
    s = int(track_count * delay)
    if s < 60:
        return f"{s} сек"
    return f"{s//60} мин"
