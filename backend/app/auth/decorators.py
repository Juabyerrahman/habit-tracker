from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.errors import ApiError
from app.extensions import db
from app.models import User


def auth_required(fn):
    """Verifies the Bearer access token and loads the user into g.user."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = db.session.get(User, get_jwt_identity())
        if user is None or not user.is_active:
            raise ApiError(401, "invalid_token", "Account not found or disabled.")
        g.user = user
        return fn(*args, **kwargs)

    return wrapper
