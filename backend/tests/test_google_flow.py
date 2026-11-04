"""Google authorization-code flow. Google's token endpoint and signature check are faked;
everything else (state, nonce, PKCE, cookies, user creation, linking) runs for real."""
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from app.auth import google_flow
from app.auth.providers import init_providers
from app.auth.providers import google as google_provider
from app.models import AuthIdentity, User
from tests.conftest import PASSWORD, register, signup

CLIENT_ID = "test-client.apps.googleusercontent.com"


class FakeResp:
    def __init__(self, status, payload):
        self.status_code, self._payload = status, payload

    def json(self):
        return self._payload


class FakeGoogle:
    def __init__(self):
        self.calls, self.status, self.exc, self.claims = [], 200, None, {}

    def post(self, url, data=None, timeout=None, **kw):
        self.calls.append({"url": url, "data": data})
        if self.exc:
            raise self.exc
        return FakeResp(self.status, {"id_token": "fake.jwt.token"} if self.status == 200 else {"error": "invalid_grant"})

    def verify(self, token, request, audience):
        assert audience == CLIENT_ID  # audience is always OUR client id
        return dict(self.claims)

    def will_return(self, params, **claims):
        self.claims = {"sub": "g-1", "email": "user@example.com", "email_verified": True, "name": "G User",
                       "nonce": params["nonce"], **claims}


@pytest.fixture()
def gapp(app):
    app.config.update(GOOGLE_CLIENT_ID=CLIENT_ID, GOOGLE_CLIENT_SECRET=secrets.token_hex(16), ENABLE_DEV_TOOLS=False)
    init_providers(app)
    return app


@pytest.fixture()
def google(gapp, monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(google_flow.requests, "post", fake.post)
    monkeypatch.setattr(google_provider.id_token, "verify_oauth2_token", fake.verify)
    return fake


def start(client, query=""):
    r = client.get("/auth/google/login" + query)
    assert r.status_code == 302, r.headers
    loc = urlparse(r.headers["Location"])
    return r, {k: v[0] for k, v in parse_qs(loc.query).items()}, loc


def callback(client, params, code="auth-code", state=None):
    return client.get("/auth/google/callback", query_string={"code": code, "state": state or params["state"]})


def error_url(app, code):
    return f"{app.config['GOOGLE_ERROR_URL']}?error={code}"


def no_session(client):
    return client.get_cookie("refresh_token", path="/api/auth") is None


# ---------- happy path ----------
def test_login_redirect_is_correct_and_leaks_no_secret(gapp, client):
    r, p, loc = start(client)
    assert (loc.netloc, loc.path) == ("accounts.google.com", "/o/oauth2/v2/auth")
    assert p["client_id"] == CLIENT_ID and p["response_type"] == "code"
    assert p["redirect_uri"] == "http://localhost:5000/auth/google/callback"
    assert p["scope"].split() == ["openid", "email", "profile"]
    assert p["code_challenge_method"] == "S256" and p["state"] and p["nonce"]
    assert gapp.config["GOOGLE_CLIENT_SECRET"] not in r.headers["Location"]
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "Path=/auth/google" in cookie and "SameSite=Lax" in cookie
    assert gapp.config["GOOGLE_CLIENT_SECRET"] not in cookie


def test_full_flow_creates_user_and_session(gapp, client, google):
    _, p, _ = start(client, "?tz=Asia/Dhaka")
    google.will_return(p, email="New.User@Example.com")
    cb = callback(client, p)
    assert cb.status_code == 302 and cb.headers["Location"] == gapp.config["GOOGLE_SUCCESS_URL"]

    sent = google.calls[0]
    assert sent["url"] == google_flow.TOKEN_URL
    assert sent["data"]["client_secret"] == gapp.config["GOOGLE_CLIENT_SECRET"]  # only ever in this server-to-server call
    assert sent["data"]["grant_type"] == "authorization_code" and sent["data"]["code"] == "auth-code"
    digest = base64.urlsafe_b64encode(hashlib.sha256(sent["data"]["code_verifier"].encode()).digest()).rstrip(b"=")
    assert digest.decode() == p["code_challenge"]  # PKCE verifier matches the challenge sent to Google
    assert gapp.config["GOOGLE_CLIENT_SECRET"] not in cb.headers["Location"]

    # the browser exchanges the refresh cookie for an access token through the EXISTING endpoint
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200
    body = r.get_json()
    assert body["user"]["email"] == "new.user@example.com" and body["user"]["email_verified"] is True
    assert body["user"]["timezone"] == "Asia/Dhaka" and body["user"]["auth_providers"] == ["google"]
    me = client.get("/api/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_returning_google_user_gets_same_account(gapp, client, google):
    for _ in range(2):
        c = gapp.test_client()
        _, p, _ = start(c)
        google.will_return(p)
        assert callback(c, p).headers["Location"] == gapp.config["GOOGLE_SUCCESS_URL"]
    assert User.query.count() == 1 and AuthIdentity.query.filter_by(provider="google").count() == 1


def test_logout_revokes_google_session(gapp, client, google):
    _, p, _ = start(client)
    google.will_return(p)
    callback(client, p)
    raw = client.get_cookie("refresh_token", path="/api/auth").value
    assert client.post("/api/auth/logout").status_code == 204
    client.set_cookie("refresh_token", raw, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401


# ---------- attacks and failures ----------
def test_state_mismatch_is_rejected_before_any_google_call(gapp, client, google):
    _, p, _ = start(client)
    google.will_return(p)
    cb = callback(client, p, state="attacker-state")
    assert cb.headers["Location"] == error_url(gapp, "invalid_state")
    assert google.calls == [] and User.query.count() == 0 and no_session(client)


def test_missing_tampered_or_expired_state_cookie(gapp, client, google, monkeypatch):
    _, p, _ = start(client)
    google.will_return(p)
    fresh = gapp.test_client()  # no state cookie at all
    assert callback(fresh, p).headers["Location"] == error_url(gapp, "invalid_state")
    client.set_cookie("google_oauth_state", "garbage", path="/auth/google")
    assert callback(client, p).headers["Location"] == error_url(gapp, "invalid_state")
    c3 = gapp.test_client()
    _, p3, _ = start(c3)
    monkeypatch.setattr(google_flow, "STATE_TTL_SECONDS", -1)
    assert callback(c3, p3).headers["Location"] == error_url(gapp, "invalid_state")
    assert google.calls == [] and User.query.count() == 0


def test_state_cookie_is_single_use(gapp, client, google):
    _, p, _ = start(client)
    google.will_return(p)
    assert callback(client, p).headers["Location"] == gapp.config["GOOGLE_SUCCESS_URL"]
    replay = callback(client, p)
    assert replay.headers["Location"] == error_url(gapp, "invalid_state")
    assert len(google.calls) == 1


def test_wrong_nonce_is_rejected(gapp, client, google):
    _, p, _ = start(client)
    google.will_return(p, nonce="replayed-from-another-login")
    assert callback(client, p).headers["Location"] == error_url(gapp, "invalid_credential")
    assert User.query.count() == 0 and no_session(client)


def test_unverified_google_email_rejected(gapp, client, google):
    _, p, _ = start(client)
    google.will_return(p, email_verified=False)
    assert callback(client, p).headers["Location"] == error_url(gapp, "email_not_verified")
    assert User.query.count() == 0


def test_user_cancelled_consent(gapp, client, google):
    _, p, _ = start(client)
    r = client.get("/auth/google/callback", query_string={"error": "access_denied", "state": p["state"]})
    assert r.headers["Location"] == error_url(gapp, "access_denied") and google.calls == []


def test_missing_code(gapp, client, google):
    _, p, _ = start(client)
    r = client.get("/auth/google/callback", query_string={"state": p["state"]})
    assert r.headers["Location"] == error_url(gapp, "missing_code")


def test_code_exchange_failure_and_network_error(gapp, client, google):
    _, p, _ = start(client)
    google.status = 400
    assert callback(client, p).headers["Location"] == error_url(gapp, "code_exchange_failed")
    c2 = gapp.test_client()
    _, p2, _ = start(c2)
    google.status, google.exc = 200, requests.ConnectionError("down")
    assert callback(c2, p2).headers["Location"] == error_url(gapp, "provider_unavailable")


def test_not_configured(app, client):
    assert start_error(client) == error_url(app, "provider_not_configured")
    app.config["GOOGLE_CLIENT_ID"] = CLIENT_ID  # id but no secret -> still disabled for the code flow
    init_providers(app)
    assert start_error(client) == error_url(app, "provider_not_configured")


def start_error(client):
    r = client.get("/auth/google/login")
    assert r.status_code == 302
    return r.headers["Location"]


# ---------- existing accounts / duplicate emails ----------
def test_existing_password_account_is_not_hijacked(gapp, client, google):
    register(client, "dup@example.com")
    c = gapp.test_client()
    _, p, _ = start(c)
    google.will_return(p, email="dup@example.com")
    assert callback(c, p).headers["Location"] == error_url(gapp, "account_exists")
    assert AuthIdentity.query.filter_by(provider="google").count() == 0 and no_session(c)
    login = gapp.test_client().post("/api/auth/login", json={"email": "dup@example.com", "password": PASSWORD})
    assert login.status_code == 200  # email/password login untouched


def test_signed_in_user_can_link_google_then_use_either(gapp, client, google):
    h = signup(client, "me@example.com")
    r = client.post("/api/auth/google/link", headers=h, json={})
    assert r.status_code == 200
    p = {k: v[0] for k, v in parse_qs(urlparse(r.get_json()["authorization_url"]).query).items()}
    google.will_return(p, sub="g-link", email="me@example.com")
    cb = callback(client, p)
    assert cb.headers["Location"] == f"{gapp.config['GOOGLE_SUCCESS_URL']}?linked=google"

    me = client.get("/api/me", headers=h).get_json()["user"]
    assert me["auth_providers"] == ["google", "password"] and me["email_verified"] is True

    c2 = gapp.test_client()  # Google login now lands on the same account
    _, p2, _ = start(c2)
    google.will_return(p2, sub="g-link", email="me@example.com")
    callback(c2, p2)
    assert c2.post("/api/auth/refresh").get_json()["user"]["id"] == me["id"]
    assert User.query.count() == 1
    ok = gapp.test_client().post("/api/auth/login", json={"email": "me@example.com", "password": PASSWORD})
    assert ok.status_code == 200


def test_link_requires_auth_and_rejects_identity_of_another_user(gapp, client, google):
    assert client.post("/api/auth/google/link", json={}).status_code == 401
    c = gapp.test_client()
    _, p, _ = start(c)
    google.will_return(p, sub="taken", email="owner@example.com")
    callback(c, p)
    h = signup(client, "mine@example.com")
    url = client.post("/api/auth/google/link", headers=h, json={}).get_json()["authorization_url"]
    p2 = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    google.will_return(p2, sub="taken", email="owner@example.com")
    assert callback(client, p2).headers["Location"] == error_url(gapp, "identity_in_use")


# ---------- redirect targets / dev page ----------
def test_return_target_is_allow_listed(gapp, client, google):
    _, p, _ = start(client, "?return=https://evil.example/steal")
    google.will_return(p)
    assert callback(client, p).headers["Location"] == gapp.config["GOOGLE_SUCCESS_URL"]  # never an attacker URL
    c = gapp.test_client()
    _, p, _ = start(c, "?return=dev")  # dev disabled -> falls back to the app
    google.will_return(p, sub="g-2", email="two@example.com")
    assert callback(c, p).headers["Location"] == gapp.config["GOOGLE_SUCCESS_URL"]


def test_dev_page_and_dev_return(gapp, client, google):
    assert client.get("/dev/auth-test").status_code == 404
    gapp.config["ENABLE_DEV_TOOLS"] = True
    page = client.get("/dev/auth-test")
    assert page.status_code == 200 and gapp.config["GOOGLE_CLIENT_SECRET"] not in page.get_data(as_text=True)
    _, p, _ = start(client, "?return=dev")
    google.will_return(p)
    assert callback(client, p).headers["Location"] == "/dev/auth-test"
    c = gapp.test_client()
    _, p, _ = start(c, "?return=dev")
    r = callback(c, p, state="wrong")
    assert r.headers["Location"] == "/dev/auth-test?error=invalid_state"


def test_existing_oauth_endpoint_still_works(gapp, client, google):
    google.claims = {"sub": "gis-1", "email": "gis@example.com", "email_verified": True, "name": "G"}
    r = client.post("/api/auth/oauth/google", json={"credential": "gis-id-token"})
    assert r.status_code == 200 and r.get_json()["user"]["auth_providers"] == ["google"]
