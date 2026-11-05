from app.extensions import db
from app.models.base import IdMixin
from app.utils.time import utcnow


class HabitArchivePeriod(IdMixin, db.Model):
    __tablename__ = "habit_archive_periods"

    __table_args__ = (
        db.Index(
            "ix_habit_archive_habit_start",
            "habit_id",
            "archived_from",
        ),
        db.Index(
            "uq_habit_archive_one_open",
            "habit_id",
            unique=True,
            sqlite_where=db.text("restored_at IS NULL"),
            postgresql_where=db.text("restored_at IS NULL"),
        ),
    )

    habit_id = db.Column(
        db.String(36),
        db.ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
    )

    archived_from = db.Column(db.DateTime, nullable=False)
    restored_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
    )
