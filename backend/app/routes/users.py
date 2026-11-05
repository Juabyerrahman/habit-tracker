from flask import Blueprint, g, jsonify, request

from app.auth.decorators import auth_required
from app.extensions import db
from app.schemas import load
from app.schemas.auth import ProfileUpdateSchema

bp = Blueprint("users", __name__, url_prefix="/api/me")


@bp.get("")
@auth_required
def get_me():
    return jsonify({"user": g.user.to_dict()})


@bp.patch("")
@auth_required
def update_me():
    data = load(ProfileUpdateSchema(), request.get_json(silent=True))
    for key, value in data.items():
        setattr(g.user, key, value)
    db.session.commit()
    return jsonify({"user": g.user.to_dict()})
