from datetime import date, datetime

from app.errors import ApiError


def parse_day(value: str, field: str = "date") -> date:
    """Strict YYYY-MM-DD parser."""
    try:
        if len(value) != 10:
            raise ValueError
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ApiError(422, "invalid_date", f"'{field}' must be a date in YYYY-MM-DD format.") from None
