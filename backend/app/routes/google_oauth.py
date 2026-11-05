from urllib.parse import urlencode

from flask import Blueprint, current_app, g, jsonify, redirect, request
from marshmallow import ValidationError

from app.auth import google_flow, service
from app.auth.cookies import set_refresh_cookie
from app.auth.decorators import auth_required
from app.errors import ApiError
from app.extensions import db, limiter
from app.models import User
from app.schemas.common import valid_timezone

bp = Blueprint("google_oauth", __name__)

DEV_PAGE = "/dev/auth-test"


def _set_state_cookie(resp, value: str) -> None:
    resp.set_cookie(
        google_flow.STATE_COOKIE,
        value,
        max_age=google_flow.STATE_TTL_SECONDS,
        httponly=True,
        secure=current_app.config["COOKIE_SECURE"],
        samesite="Lax",  # must be Lax: Google redirects back with a cross-site top-level GET
        path=google_flow.STATE_COOKIE_PATH,
    )


def _finish_redirect(ctx, *, ok: bool, **params):
    cfg = current_app.config
    if (ctx or {}).get("return") == "dev" and cfg["ENABLE_DEV_TOOLS"]:
        base = DEV_PAGE
    else:
        base = cfg["GOOGLE_SUCCESS_URL"] if ok else cfg["GOOGLE_ERROR_URL"]
    if params:
        base += ("&" if "?" in base else "?") + urlencode(params)
    resp = redirect(base, 302)
    resp.delete_cookie(google_flow.STATE_COOKIE, path=google_flow.STATE_COOKIE_PATH)  # single use
    return resp


@bp.get("/auth/google/login")
@limiter.limit("20 per minute")
def google_login():
    tz = request.args.get("tz")
    try:
        if tz:
            valid_timezone(tz)
    except ValidationError:
        tz = None
    try:
        url, cookie = google_flow.begin(return_to=request.args.get("return", "app"), timezone=tz or None)
    except ApiError as e:
        return _finish_redirect(None, ok=False, error=e.code)
    resp = redirect(url, 302)
    _set_state_cookie(resp, cookie)
    return resp


@bp.get("/auth/google/callback")
@limiter.limit("20 per minute")
def google_callback():
    ctx = google_flow.read_state(request.cookies.get(google_flow.STATE_COOKIE))
    try:
        if request.args.get("error"):  # user cancelled / Google refused
            code = "access_denied" if request.args["error"] == "access_denied" else "google_error"
            raise ApiError(400, code, "Google sign-in was cancelled.")
        identity = google_flow.finish(ctx, request.args.get("state"), request.args.get("code"))

        if ctx.get("link"):  # signed-in user connecting Google to their existing account
            user = db.session.get(User, ctx["link"])
            if user is None or not user.is_active:
                raise ApiError(401, "invalid_session", "Please sign in again.")
            service.link_identity(user, identity)
            return _finish_redirect(ctx, ok=True, linked="google")

        result = service.login_with_identity(identity, ctx.get("tz") or "UTC")  # same path as every provider
        resp = _finish_redirect(ctx, ok=True)
        set_refresh_cookie(resp, result["refresh_token"])  # the browser gets its access token via /api/auth/refresh
        return resp
    except ApiError as e:
        db.session.rollback()
        return _finish_redirect(ctx, ok=False, error=e.code)
    except Exception:
        current_app.logger.exception("Unexpected error in Google callback")
        db.session.rollback()
        return _finish_redirect(ctx, ok=False, error="server_error")


@bp.post("/api/auth/google/link")
@limiter.limit("10 per minute")
@auth_required
def google_link_start():
    """Signed-in user -> returns the Google URL to navigate to; the callback then links the account."""
    body = request.get_json(silent=True)
    return_to = body.get("return", "app") if isinstance(body, dict) else "app"
    url, cookie = google_flow.begin(return_to=return_to, link_user_id=g.user.id)
    resp = jsonify({"authorization_url": url})
    _set_state_cookie(resp, cookie)
    return resp
