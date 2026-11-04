from flask import Blueprint, current_app, g, jsonify, make_response, request

from app.auth import service, tokens
from app.auth.cookies import clear_refresh_cookie as _clear_refresh_cookie
from app.auth.cookies import set_refresh_cookie as _set_refresh_cookie
from app.auth.decorators import auth_required
from app.auth.providers import enabled_providers, get_provider
from app.errors import ApiError, error_response
from app.extensions import db, limiter
from app.schemas import load
from app.schemas.auth import LoginSchema, OAuthSchema, RegisterSchema

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _session_response(result: dict, status: int = 200):
    resp = make_response(
        jsonify(
            {
                "user": result["user"].to_dict(),
                "access_token": result["access_token"],
                "token_type": "Bearer",
                "expires_in": result["expires_in"],
            }
        ),
        status,
    )
    _set_refresh_cookie(resp, result["refresh_token"])
    return resp


@bp.get("/providers")
def providers():
    return jsonify({"providers": enabled_providers()})


@bp.post("/register")
@limiter.limit("5 per minute")
def register():
    data = load(RegisterSchema(), request.get_json(silent=True))
    return _session_response(service.register_with_password(**data), 201)


@bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = load(LoginSchema(), request.get_json(silent=True))
    return _session_response(service.login_with_password(**data))


@bp.post("/oauth/<provider>")
@limiter.limit("20 per minute")
def oauth_login(provider):
    data = load(OAuthSchema(), request.get_json(silent=True))
    identity = get_provider(provider).verify(data["credential"])
    return _session_response(service.login_with_identity(identity, data.get("timezone", "UTC")))


@bp.post("/link/<provider>")
@limiter.limit("10 per minute")
@auth_required
def oauth_link(provider):
    data = load(OAuthSchema(), request.get_json(silent=True))
    identity = get_provider(provider).verify(data["credential"])
    user = service.link_identity(g.user, identity)
    return jsonify({"user": user.to_dict()})


@bp.post("/refresh")
@limiter.limit("30 per minute")
def refresh():
    raw = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    try:
        if not raw:
            raise ApiError(401, "missing_refresh_token", "Not signed in.")
        result = service.refresh_session(raw)
    except ApiError as e:
        resp = make_response(*error_response(e.status, e.code, e.message))
        _clear_refresh_cookie(resp)
        return resp
    return _session_response(result)


@bp.post("/logout")
def logout():
    raw = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    if raw:
        tokens.revoke_token_family(raw)
        db.session.commit()
    resp = make_response("", 204)
    _clear_refresh_cookie(resp)
    return resp


@bp.post("/logout-all")
@auth_required
def logout_all():
    tokens.revoke_all_for_user(g.user.id)
    db.session.commit()
    resp = make_response("", 204)
    _clear_refresh_cookie(resp)
    return resp
