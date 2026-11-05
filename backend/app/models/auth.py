from app.extensions import db
from app.models.base import IdMixin
from app.utils.time import utcnow


class AuthIdentity(IdMixin, db.Model):
    """One way a user can sign in. 'password' and every OAuth provider use this same table,
    so adding a provider never touches the users table."""

    __tablename__ = "auth_identities"
    __table_args__ = (
        db.UniqueConstraint("provider", "subject", name="uq_identity_provider_subject"),
        db.UniqueConstraint("user_id", "provider", name="uq_identity_user_provider"),
    )

    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = db.Column(db.String(32), nullable=False)
    subject = db.Column(db.String(255), nullable=False)  # provider's stable user id ('password': our user id)
    secret_hash = db.Column(db.String(255))  # argon2 hash, only for provider='password'
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="identities")


class RefreshToken(IdMixin, db.Model):
    """Opaque, rotating refresh tokens. Only a SHA-256 hash is stored."""

    __tablename__ = "refresh_tokens"

    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = db.Column(db.String(36), nullable=False, index=True)  # one family per login/device
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
