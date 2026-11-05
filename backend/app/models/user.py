from app.extensions import db
from app.models.base import IdMixin, TimestampMixin, iso


class User(IdMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    name = db.Column(db.String(100), nullable=False, default="")
    timezone = db.Column(db.String(64), nullable=False, default="UTC")
    week_starts_on = db.Column(db.SmallInteger, nullable=False, default=0)  # 0=Mon .. 6=Sun
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    identities = db.relationship("AuthIdentity", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "email_verified": self.email_verified,
            "name": self.name,
            "timezone": self.timezone,
            "week_starts_on": self.week_starts_on,
            "auth_providers": sorted(i.provider for i in self.identities),
            "created_at": iso(self.created_at),
        }
