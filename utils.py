"""General utilities."""
import re
from datetime import datetime
from datetime import timezone as dt_timezone

try:
    import pytz
except ImportError:  # pragma: no cover - production installs pytz
    from zoneinfo import ZoneInfo

    class _PytzCompat:
        @staticmethod
        def timezone(name: str):
            try:
                return ZoneInfo(name)
            except Exception:
                return dt_timezone.utc

    pytz = _PytzCompat()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if value and value.startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    raise ValueError("Phone number must be E.164 or a US 10-digit number")


def now_in_timezone(tz_name: str) -> datetime:
    return datetime.now(pytz.timezone(tz_name))


def inside_calling_window(tz_name: str, at: datetime | None = None) -> bool:
    local = at.astimezone(pytz.timezone(tz_name)) if at else now_in_timezone(tz_name)
    if local.weekday() <= 4:
        return 9 <= local.hour < 19
    if local.weekday() == 5:
        return 10 <= local.hour < 17
    return False
