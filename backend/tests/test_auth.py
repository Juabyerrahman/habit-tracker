import pytest

from app.auth.providers.base import IdentityProvider, VerifiedIdentity
from app.errors import ApiError
from app.extensions import db
from app.models import AuthIdentity, RefreshToken, User
from tests.conftest import PASSWORD, register, signup


# ---------- password auth ----------
def test_register_returns_token_and_httponly_cookie(client):
    r = register(client, name="Jubayer", timezone="Asia/Dhaka")
    assert r.status_code == 201
    body = r.get_json()
    assert body["token_type"] == "Bearer" and body["access_token"]
    assert body["user"]["email"] == "a@example.com" and body["user"]["timezone"] == "Asia/Dhaka"
    assert not {"password", "password_hash", "secret_hash"} & set(body["user"])
    assert "argon2" not in str(body)
    cookie = r.headers["Set-Cookie"]
    assert "refresh_token=" in cookie and "HttpOnly" in cookie and "Path=/api/auth" in cookie
    assert body["access_token"] not in cookie


def test_password_is_hashed_with_argon2(app, client):
    register(client)
    identity = AuthIdentity.query.filter_by(provider="password").one()
    assert identity.secret_hash.startswith("$argon2id$") and PASSWORD not in identity.secret_hash


def test_duplicate_email_is_case_insensitive(client):
    assert register(client, "A@Example.com").status_code == 201
    r = register(client, "a@example.COM")
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "email_taken"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "x@example.com", "password": "short"},
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "x@example.com", "password": PASSWORD, "timezone": "Mars/Base"},
        {"email": "x@example.com", "password": PASSWORD, "is_admin": True},  # unknown field
        {"password": PASSWORD},
    ],
)
def test_register_validation(client, payload):
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "validation_error"


def test_non_json_body_rejected(client):
    r = client.post("/api/auth/register", data="email=a", content_type="text/plain")
    assert r.status_code == 400


def test_login_success_and_generic_failure(client):
    register(client)
    ok = client.post("/api/auth/login", json={"email": "A@example.com", "password": PASSWORD})
    assert ok.status_code == 200 and ok.get_json()["access_token"]
    wrong = client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope-nope-nope"})
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope-nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()  # no account enumeration


def test_protected_routes_require_valid_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    h = signup(client)
    r = client.get("/api/me", headers=h)
    assert r.status_code == 200 and r.get_json()["user"]["email"] == "a@example.com"


def test_update_profile(client, auth):
    r = client.patch("/api/me", headers=auth, json={"timezone": "Asia/Dhaka", "week_starts_on": 5})
    assert r.status_code == 200 and r.get_json()["user"]["week_starts_on"] == 5
    assert client.patch("/api/me", headers=auth, json={}).status_code == 422
    assert client.patch("/api/me", headers=auth, json={"email": "x@y.com"}).status_code == 422


# ---------- refresh / logout ----------
def test_refresh_rotates_and_reuse_revokes_family(app, client):
    register(client)
    old_cookie = client.get_cookie("refresh_token", path="/api/auth").value
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200 and r.get_json()["access_token"]
    new_cookie = client.get_cookie("refresh_token", path="/api/auth").value
    assert new_cookie != old_cookie

    # attacker replays the already-used token
    client.set_cookie("refresh_token", old_cookie, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401
    # family is dead, so the legitimately rotated token no longer works either
    client.set_cookie("refresh_token", new_cookie, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401


def test_refresh_without_cookie(client):
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "missing_refresh_token"


def test_refresh_token_stored_hashed(app, client):
    register(client)
    raw = client.get_cookie("refresh_token", path="/api/auth").value
    assert RefreshToken.query.one().token_hash != raw


def test_logout_revokes_session(client):
    register(client)
    raw = client.get_cookie("refresh_token", path="/api/auth").value
    assert client.post("/api/auth/logout").status_code == 204
    client.set_cookie("refresh_token", raw, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401


def test_logout_all(app, client):
    h = signup(client)
    other = app.test_client()
    other.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert client.post("/api/auth/logout-all", headers=h).status_code == 204
    assert other.post("/api/auth/refresh").status_code == 401


# ---------- provider plug-in architecture ----------
class FakeProvider(IdentityProvider):
    name = "fake"

    def __init__(self, identity):
        self.identity = identity

    def verify(self, credential):
        if credential == "bad":
            raise ApiError(401, "invalid_credential", "nope")
        return self.identity


def install(app, **kw):
    ident = VerifiedIdentity("fake", kw.get("sub", "sub-1"), kw.get("email", "g@example.com"), kw.get("verified", True), "G")
    app.extensions["identity_providers"]["fake"] = FakeProvider(ident)


def test_google_disabled_without_client_id(client):
    assert client.get("/api/auth/providers").get_json() == {"providers": []}
    r = client.post("/api/auth/oauth/google", json={"credential": "x"})
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "unknown_provider"


def test_oauth_creates_then_reuses_account(app, client):
    install(app)
    first = client.post("/api/auth/oauth/fake", json={"credential": "ok", "timezone": "Asia/Dhaka"})
    assert first.status_code == 200
    user = first.get_json()["user"]
    assert user["email_verified"] is True and user["timezone"] == "Asia/Dhaka" and user["auth_providers"] == ["fake"]
    again = client.post("/api/auth/oauth/fake", json={"credential": "ok"})
    assert again.get_json()["user"]["id"] == user["id"] and User.query.count() == 1


def test_oauth_rejects_bad_credential(app, client):
    install(app)
    assert client.post("/api/auth/oauth/fake", json={"credential": "bad"}).status_code == 401


def test_oauth_does_not_hijack_unverified_password_account(app, client):
    register(client, "g@example.com")
    install(app, email="g@example.com")
    r = app.test_client().post("/api/auth/oauth/fake", json={"credential": "ok"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "account_exists"


def test_link_provider_to_existing_account(app, client):
    h = signup(client, "g@example.com")
    install(app, email="g@example.com")
    r = client.post("/api/auth/link/fake", headers=h, json={"credential": "ok"})
    assert r.status_code == 200
    user = r.get_json()["user"]
    assert user["auth_providers"] == ["fake", "password"] and user["email_verified"] is True
    # now OAuth login reaches the same account
    login = app.test_client().post("/api/auth/oauth/fake", json={"credential": "ok"})
    assert login.get_json()["user"]["id"] == user["id"]


def test_cannot_link_identity_owned_by_another_user(app, client):
    install(app, email="other@example.com")
    app.test_client().post("/api/auth/oauth/fake", json={"credential": "ok"})
    h = signup(client, "mine@example.com")
    r = client.post("/api/auth/link/fake", headers=h, json={"credential": "ok"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "identity_in_use"


# ---------- real Google provider (token verification mocked) ----------
def test_google_provider_verification(monkeypatch):
    from app.auth.providers import google

    provider = google.GoogleProvider("client-id")
    good = {"sub": "123", "email": "U@Example.com", "email_verified": True, "name": "U"}
    monkeypatch.setattr(google.id_token, "verify_oauth2_token", lambda *a, **k: good)
    ident = provider.verify("tok")
    assert (ident.provider, ident.subject, ident.email) == ("google", "123", "u@example.com")

    monkeypatch.setattr(google.id_token, "verify_oauth2_token", lambda *a, **k: {**good, "email_verified": False})
    with pytest.raises(ApiError) as e:
        provider.verify("tok")
    assert e.value.status == 403

    def boom(*a, **k):
        raise ValueError("bad signature")

    monkeypatch.setattr(google.id_token, "verify_oauth2_token", boom)
    with pytest.raises(ApiError) as e:
        provider.verify("tok")
    assert e.value.status == 401
