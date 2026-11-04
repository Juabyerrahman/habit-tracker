from app.extensions import db
from app.models.base import IdMixin, TimestampMixin, iso
from app.utils.time import utcnow


def weekdays_to_mask(days) -> int:
    mask = 0
    for d in set(days):
        mask |= 1 << d
    return mask


def mask_to_weekdays(mask: int) -> list[int]:
    return [d for d in range(7) if mask & (1 << d)]  # 0 = Monday (matches date.weekday())


class Habit(IdMixin, TimestampMixin, db.Model):
    __tablename__ = "habits"

    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False, default="")
    category = db.Column(db.String(50))
    icon = db.Column(db.String(16))
    start_date = db.Column(db.Date, nullable=False)
    schedule_mask = db.Column(db.Integer, nullable=False, default=127)  # bit0=Mon .. bit6=Sun
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    archived_at = db.Column(db.DateTime)  # archive = remove from dashboard; history is kept forever

    completions = db.relationship("HabitCompletion", back_populates="habit")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "start_date": self.start_date.isoformat(),
            "schedule": mask_to_weekdays(self.schedule_mask),
            "sort_order": self.sort_order,
            "archived_at": iso(self.archived_at),
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }


class HabitCompletion(IdMixin, TimestampMixin, db.Model):
    """Only completions are stored. 'Missed' is derived (scheduled, past, not completed)."""

    __tablename__ = "habit_completions"
    __table_args__ = (
        db.UniqueConstraint("habit_id", "date", name="uq_completion_habit_date"),
        db.Index("ix_completion_user_date", "user_id", "date"),
    )

    habit_id = db.Column(db.String(36), db.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    deleted_at = db.Column(db.DateTime)  # tombstone so offline sync can propagate un-checks

    habit = db.relationship("Habit", back_populates="completions")
class HabitScheduleVersion(IdMixin, db.Model):
    __tablename__ = "habit_schedule_versions"

    __table_args__ = (
        db.UniqueConstraint(
            "habit_id",
            "effective_from",
            name="uq_habit_schedule_effective_from",
        ),
        db.Index(
            "ix_habit_schedule_habit_effective",
            "habit_id",
            "effective_from",
        ),
    )

    habit_id = db.Column(
        db.String(36),
        db.ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
    )

    effective_from = db.Column(db.Date, nullable=False)

    schedule_mask = db.Column(db.Integer, nullable=False)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
    )