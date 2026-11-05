import hashlib
import secrets
from datetime import timedelta

from flask import current_app

from app.errors import ApiError
from app.extensions import db
from app.models import RefreshToken, User
from app.models.base import new_id
from app.utils.time import utcnow


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _invalid() -> ApiError:
    return ApiError(401, "invalid_refresh_token", "Session expired. Please sign in again.")


def issue_refresh_token(user: User, family_id: str | None = None) -> str:
    raw = secrets.token_urlsafe(48)
    db.session.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or new_id(),
            token_hash=_hash(raw),
            expires_at=utcnow() + timedelta(days=current_app.config["REFRESH_TOKEN_DAYS"]),
        )
    )
    return raw


def rotate_refresh_token(raw: str) -> tuple[User, str]:
    """Single-use rotation. Presenting an already-used token revokes the whole family
    (a stolen token and the real client can't both keep working)."""
    token = RefreshToken.query.filter_by(token_hash=_hash(raw)).first()
    if token is None:
        raise _invalid()
    if token.revoked_at is not None:
        revoke_family(token.family_id)
        db.session.commit()
        raise _invalid()
    if token.expires_at <= utcnow():
        raise _invalid()
    user = db.session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise _invalid()
    token.revoked_at = utcnow()
    return user, issue_refresh_token(user, token.family_id)


def revoke_family(family_id: str) -> None:
    RefreshToken.query.filter_by(family_id=family_id, revoked_at=None).update({"revoked_at": utcnow()})


def revoke_token_family(raw: str) -> None:
    token = RefreshToken.query.filter_by(token_hash=_hash(raw)).first()
    if token:
        revoke_family(token.family_id)


def revoke_all_for_user(user_id: str) -> None:
    RefreshToken.query.filter_by(user_id=user_id, revoked_at=None).update({"revoked_at": utcnow()})
