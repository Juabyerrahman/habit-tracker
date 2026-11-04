from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from app.auth.decorators import auth_required
from app.errors import ApiError
from app.extensions import db
from app.models import Habit, HabitCompletion
from app.models.habit import weekdays_to_mask
from app.routes._helpers import next_sort_order, owned_or_404
from app.schemas import load
from app.schemas.habit import HabitCreateSchema, HabitUpdateSchema
from app.utils.dates import parse_day
from app.utils.time import today_in, utcnow

bp = Blueprint("habits", __name__, url_prefix="/api/habits")

MAX_RANGE_DAYS = 366


@bp.get("")
@auth_required
def list_habits():
    query = Habit.query.filter_by(user_id=g.user.id)
    if request.args.get("include_archived", "").lower() not in {"1", "true", "yes"}:
        query = query.filter(Habit.archived_at.is_(None))
    habits = query.order_by(Habit.sort_order, Habit.created_at).all()
    return jsonify({"habits": [h.to_dict() for h in habits]})


@bp.post("")
@auth_required
def create_habit():
    data = load(HabitCreateSchema(), request.get_json(silent=True))
    habit = Habit(
        user_id=g.user.id,
        name=data["name"],
        description=data["description"],
        category=data["category"],
        icon=data["icon"],
        start_date=data["start_date"] or today_in(g.user.timezone),
        schedule_mask=weekdays_to_mask(data["schedule"]),
        sort_order=next_sort_order(Habit),
    )
    db.session.add(habit)
    db.session.commit()
    return jsonify({"habit": habit.to_dict()}), 201


@bp.get("/<habit_id>")
@auth_required
def get_habit(habit_id):
    return jsonify({"habit": owned_or_404(Habit, habit_id).to_dict()})


@bp.patch("/<habit_id>")
@auth_required
def update_habit(habit_id):
    habit = owned_or_404(Habit, habit_id)
    _require_active(habit)
    data = load(HabitUpdateSchema(), request.get_json(silent=True))

    if "start_date" in data:
        earliest = (
            db.session.query(func.min(HabitCompletion.date))
            .filter(HabitCompletion.habit_id == habit.id, HabitCompletion.deleted_at.is_(None))
            .scalar()
        )
        if earliest and data["start_date"] > earliest:
            raise ApiError(422, "start_date_after_completion", f"Habit already has a completion on {earliest}.")
    if "schedule" in data:
        habit.schedule_mask = weekdays_to_mask(data.pop("schedule"))
    for key, value in data.items():
        setattr(habit, key, value)
    db.session.commit()
    return jsonify({"habit": habit.to_dict()})


@bp.post("/<habit_id>/archive")
@auth_required
def archive_habit(habit_id):
    habit = owned_or_404(Habit, habit_id)
    if habit.archived_at is None:
        habit.archived_at = utcnow()
        db.session.commit()
    return jsonify({"habit": habit.to_dict()})


@bp.post("/<habit_id>/restore")
@auth_required
def restore_habit(habit_id):
    habit = owned_or_404(Habit, habit_id)
    if habit.archived_at is not None:
        habit.archived_at = None
        db.session.commit()
    return jsonify({"habit": habit.to_dict()})


# ---- completions ----
def _require_active(habit: Habit) -> None:
    if habit.archived_at is not None:
        raise ApiError(409, "habit_archived", "Archived habits are read-only. Restore it to make changes.")


def _check_day_writable(habit: Habit, day) -> None:
    _require_active(habit)
    if day > today_in(g.user.timezone):
        raise ApiError(422, "future_date", "Future dates cannot be completed.")
    if day < habit.start_date:
        raise ApiError(422, "before_start_date", f"This habit starts on {habit.start_date}.")


@bp.get("/<habit_id>/completions")
@auth_required
def list_completions(habit_id):
    habit = owned_or_404(Habit, habit_id)
    start = parse_day(request.args.get("from", ""), "from")
    end = parse_day(request.args.get("to", ""), "to")
    if end < start or (end - start).days >= MAX_RANGE_DAYS:
        raise ApiError(422, "invalid_range", f"'from' must be <= 'to' and span at most {MAX_RANGE_DAYS} days.")
    rows = (
        HabitCompletion.query.filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.deleted_at.is_(None),
            HabitCompletion.date >= start,
            HabitCompletion.date <= end,
        )
        .order_by(HabitCompletion.date)
        .all()
    )
    return jsonify({"habit_id": habit.id, "dates": [r.date.isoformat() for r in rows]})


@bp.put("/<habit_id>/completions/<day>")
@auth_required
def set_completion(habit_id, day):
    habit = owned_or_404(Habit, habit_id)
    d = parse_day(day)
    _check_day_writable(habit, d)
    row = HabitCompletion.query.filter_by(habit_id=habit.id, date=d).first()  # idempotent upsert
    if row is None:
        db.session.add(HabitCompletion(habit_id=habit.id, user_id=g.user.id, date=d))
    elif row.deleted_at is not None:
        row.deleted_at = None
        row.updated_at = utcnow()
    db.session.commit()
    return jsonify({"habit_id": habit.id, "date": d.isoformat(), "completed": True})


@bp.delete("/<habit_id>/completions/<day>")
@auth_required
def clear_completion(habit_id, day):
    habit = owned_or_404(Habit, habit_id)
    d = parse_day(day)
    _check_day_writable(habit, d)
    row = HabitCompletion.query.filter_by(habit_id=habit.id, date=d).first()
    if row is not None and row.deleted_at is None:
        row.deleted_at = utcnow()
        row.updated_at = utcnow()
        db.session.commit()
    return jsonify({"habit_id": habit.id, "date": d.isoformat(), "completed": False})
