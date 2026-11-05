from app.extensions import db
from app.models.base import IdMixin
from app.utils.time import utcnow


class Report(IdMixin, db.Model):
    """Snapshot of a generated weekly/monthly report (logic arrives in Phase 5)."""

    __tablename__ = "reports"
    __table_args__ = (db.UniqueConstraint("user_id", "type", "period_start", name="uq_report_period"),)

    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(10), nullable=False)  # 'weekly' | 'monthly'
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
