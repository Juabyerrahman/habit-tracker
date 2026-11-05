from app.extensions import db
from app.models.base import IdMixin, TimestampMixin, iso


class Task(IdMixin, TimestampMixin, db.Model):
    __tablename__ = "tasks"
    __table_args__ = (db.Index("ix_task_user_date", "user_id", "date"),)

    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.String(1000), nullable=False, default="")
    date = db.Column(db.Date, nullable=False)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    carried_from_task_id = db.Column(db.String(36), db.ForeignKey("tasks.id", ondelete="SET NULL"))
    deleted_at = db.Column(db.DateTime)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "notes": self.notes,
            "date": self.date.isoformat(),
            "is_completed": self.is_completed,
            "completed_at": iso(self.completed_at),
            "sort_order": self.sort_order,
            "carried_from_task_id": self.carried_from_task_id,
        }
