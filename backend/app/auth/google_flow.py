"""Google OpenID Connect, authorization-code flow with PKCE.

The browser is only ever redirected; the code is exchanged server-side where the client
secret lives. Per-login values (state, nonce, PKCE verifier) travel in a short-lived,
signed, HttpOnly cookie, so no server-side session store is needed.
"""
import base64
import hashlib
import hmac
import secrets
from urllib.parse import urlencode

import requests
from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.auth.providers import get_provider
from app.auth.providers.base import VerifiedIdentity
from app.errors import ApiError

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "openid email profile"
STATE_COOKIE = "google_oauth_state"
STATE_COOKIE_PATH = "/auth/google"
STATE_TTL_SECONDS = 600
RETURN_TARGETS = {"app", "dev"}  # fixed allow-list: the redirect target is never taken from user input


def is_configured() -> bool:
    cfg = current_app.config
    return bool(
        cfg.get("GOOGLE_CLIENT_ID")
        and cfg.get("GOOGLE_CLIENT_SECRET")
        and "google" in current_app.extensions["identity_providers"]
    )


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["JWT_SECRET_KEY"], salt="google-oauth-state")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def begin(*, return_to: str = "app", timezone: str | None = None, link_user_id: str | None = None):
    """Returns (google_authorization_url, signed_state_cookie_value)."""
    if not is_configured():
        raise ApiError(503, "provider_not_configured", "Google sign-in is not configured.")
    if return_to not in RETURN_TARGETS or (return_to == "dev" and not current_app.config["ENABLE_DEV_TOOLS"]):
        return_to = "app"

    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    query = urlencode(
        {
            "client_id": current_app.config["GOOGLE_CLIENT_ID"],
            "redirect_uri": current_app.config["GOOGLE_REDIRECT_URI"],
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
            "nonce": nonce,
            "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    cookie = _serializer().dumps(
        {"state": state, "nonce": nonce, "verifier": verifier, "return": return_to, "tz": timezone, "link": link_user_id}
    )
    return f"{AUTH_URL}?{query}", cookie


def read_state(cookie_value: str | None) -> dict | None:
    if not cookie_value:
        return None
    try:
        ctx = _serializer().loads(cookie_value, max_age=STATE_TTL_SECONDS)
    except BadSignature:  # tampered, or expired (SignatureExpired is a subclass)
        return None
    return ctx if isinstance(ctx, dict) else None


def _exchange_code(code: str, verifier: str) -> str:
    cfg = current_app.config
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cfg["GOOGLE_CLIENT_ID"],
                "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": cfg["GOOGLE_REDIRECT_URI"],
                "code_verifier": verifier,
            },
            timeout=10,
        )
    except requests.RequestException:
        raise ApiError(503, "provider_unavailable", "Google could not be reached. Try again shortly.") from None
    try:
        payload = resp.json()
    except ValueError:
        payload = {}
    if resp.status_code != 200 or not payload.get("id_token"):
        # Log only Google's error code (e.g. invalid_grant, invalid_client): never the body, code or secret.
        current_app.logger.warning("Google token exchange failed: %s", payload.get("error", resp.status_code))
        raise ApiError(401, "code_exchange_failed", "Google sign-in could not be completed.")
    return payload["id_token"]


def finish(ctx: dict | None, state_param: str | None, code: str | None) -> VerifiedIdentity:
    """Validate state, exchange the code, verify the ID token (signature, aud, iss, exp, nonce)."""
    if not ctx or not state_param or not hmac.compare_digest(str(ctx.get("state", "")), state_param):
        raise ApiError(400, "invalid_state", "Sign-in session expired or invalid. Please try again.")
    if not code:
        raise ApiError(400, "missing_code", "Google did not return an authorization code.")
    id_token = _exchange_code(code, ctx["verifier"])
    return get_provider("google").verify(id_token, nonce=ctx["nonce"])
