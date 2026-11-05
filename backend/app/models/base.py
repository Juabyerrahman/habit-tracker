import uuid

from app.extensions import db
from app.utils.time import utcnow


def new_id() -> str:
    return str(uuid.uuid4())


def iso(dt):
    """Naive-UTC datetime -> ISO-8601 with Z suffix."""
    return dt.isoformat() + "Z" if dt else None


class IdMixin:
    # UUID strings: portable across SQLite/PostgreSQL and safe to generate offline on clients.
    id = db.Column(db.String(36), primary_key=True, default=new_id)


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
