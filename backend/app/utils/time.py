from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    """Naive UTC datetime. Every timestamp in the database is UTC without tzinfo."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today_in(tz_name: str) -> date:
    """'Today' as the user experiences it. Never use server/UTC date for tracking logic."""
    return datetime.now(ZoneInfo(tz_name)).date()
