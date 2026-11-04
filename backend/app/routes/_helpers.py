from flask import g
from sqlalchemy import func

from app.errors import ApiError
from app.extensions import db


def owned_or_404(model, obj_id: str):
    """Fetch a row only if it belongs to the current user. 404 (not 403) so existence isn't leaked."""
    query = model.query.filter_by(id=obj_id, user_id=g.user.id)
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    obj = query.first()
    if obj is None:
        raise ApiError(404, "not_found", f"{model.__name__} not found.")
    return obj


def next_sort_order(model, *conditions) -> int:
    current = db.session.query(func.max(model.sort_order)).filter(model.user_id == g.user.id, *conditions).scalar()
    return 0 if current is None else current + 1
