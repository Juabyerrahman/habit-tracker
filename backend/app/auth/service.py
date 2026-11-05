"""Authentication use-cases. Provider-agnostic: password and OAuth share one session path."""
from flask import current_app
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from app.auth import passwords, tokens
from app.auth.providers.base import VerifiedIdentity
from app.errors import ApiError
from app.extensions import db
from app.models import AuthIdentity, User
from app.models.base import new_id

_BAD_LOGIN = ("invalid_credentials", "Incorrect email or password.")


def _start_session(user: User) -> dict:
    db.session.flush()  # RefreshToken has no ORM relationship to User: make sure the user row exists first
    access = create_access_token(identity=user.id)
    refresh = tokens.issue_refresh_token(user)
    db.session.commit()
    return {
        "user": user,
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    }


# ---- password ----
def register_with_password(email: str, password: str, name: str, timezone: str) -> dict:
    if User.query.filter_by(email=email).first():
        raise ApiError(409, "email_taken", "An account with this email already exists.")
    user = User(id=new_id(), email=email, name=name, timezone=timezone, email_verified=False, is_active=True)
    user.identities.append(
        AuthIdentity(provider="password", subject=user.id, secret_hash=passwords.hash_password(password))
    )
    db.session.add(user)
    try:
        db.session.flush()
    except IntegrityError:  # concurrent registration with the same email
        db.session.rollback()
        raise ApiError(409, "email_taken", "An account with this email already exists.") from None
    return _start_session(user)


def login_with_password(email: str, password: str) -> dict:
    user = User.query.filter_by(email=email).first()
    identity = next((i for i in user.identities if i.provider == "password"), None) if user else None
    if identity is None or not passwords.verify_password(identity.secret_hash, password):
        if identity is None:
            passwords.burn_time(password)
        raise ApiError(401, *_BAD_LOGIN)
    if not user.is_active:
        raise ApiError(403, "account_disabled", "This account has been disabled.")
    if passwords.needs_rehash(identity.secret_hash):
        identity.secret_hash = passwords.hash_password(password)
    return _start_session(user)


# ---- external identity (Google and future providers) ----
def login_with_identity(identity: VerifiedIdentity, timezone: str = "UTC") -> dict:
    link = AuthIdentity.query.filter_by(provider=identity.provider, subject=identity.subject).first()
    if link:
        user = link.user
    else:
        user = User.query.filter_by(email=identity.email).first()
        if user is None:
            if not identity.email_verified:
                raise ApiError(403, "email_not_verified", "The provider did not return a verified email.")
            user = User(
                id=new_id(), email=identity.email, email_verified=True, is_active=True,
                name=identity.name, timezone=timezone,
            )
            db.session.add(user)
        elif user.email_verified and identity.email_verified:
            pass  # both sides proven to control this email: safe to link
        else:
            # An unverified local account owns this email. Linking automatically would let someone
            # pre-register a victim's email and later inherit their Google login.
            raise ApiError(
                409,
                "account_exists",
                "An account with this email already exists. Sign in with your password, "
                "then link this provider from your account settings.",
            )
        user.identities.append(AuthIdentity(provider=identity.provider, subject=identity.subject))
    if not user.is_active:
        raise ApiError(403, "account_disabled", "This account has been disabled.")
    return _start_session(user)


def link_identity(user: User, identity: VerifiedIdentity) -> User:
    existing = AuthIdentity.query.filter_by(provider=identity.provider, subject=identity.subject).first()
    if existing and existing.user_id != user.id:
        raise ApiError(409, "identity_in_use", "That account is already linked to another user.")
    if existing is None:
        if any(i.provider == identity.provider for i in user.identities):
            raise ApiError(409, "provider_already_linked", "A different account of this type is already linked.")
        user.identities.append(AuthIdentity(provider=identity.provider, subject=identity.subject))
    if identity.email_verified and identity.email == user.email:
        user.email_verified = True
    db.session.commit()
    return user


# ---- sessions ----
def refresh_session(raw_refresh_token: str) -> dict:
    user, new_refresh = tokens.rotate_refresh_token(raw_refresh_token)
    access = create_access_token(identity=user.id)
    db.session.commit()
    return {
        "user": user,
        "access_token": access,
        "refresh_token": new_refresh,
        "expires_in": int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    }
