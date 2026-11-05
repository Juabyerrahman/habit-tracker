from datetime import timedelta

from flask import Blueprint, g, jsonify, request

from app.auth.decorators import auth_required
from app.errors import ApiError
from app.models import Habit
from app.services.statistics import (
    build_monthly_habit_grid,
    build_period_report,
    local_today,
    month_bounds,
)
from app.utils.dates import parse_day


bp = Blueprint("stats", __name__, url_prefix="/api")


@bp.get("/habits/grid")
@auth_required
def habit_grid():
    month = request.args.get("month", "")

    try:
        month_start, month_end = month_bounds(month)
    except ValueError as exc:
        raise ApiError(422, "invalid_month", str(exc))

    today = local_today(g.user)

    habits = (
        Habit.query
        .filter(
            Habit.user_id == g.user.id,
            Habit.archived_at.is_(None),
        )
        .order_by(Habit.sort_order, Habit.created_at)
        .all()
    )

    grids = [
        build_monthly_habit_grid(
            habit=habit,
            month_start=month_start,
            month_end=month_end,
            today=today,
            timezone_name=g.user.timezone,
        )
        for habit in habits
    ]

    return jsonify({
        "month": month,
        "today": today.isoformat(),
        "habits": grids,
    })


@bp.get("/reports/weekly")
@auth_required
def weekly_report():
    week_start_value = request.args.get("week_start", "")
    week_start = parse_day(week_start_value, "week_start")

    if week_start.weekday() != 0:
        raise ApiError(
            422,
            "invalid_week_start",
            "week_start must be a Monday.",
        )

    week_end = week_start + timedelta(days=6)

    return jsonify(
        build_period_report(
            user=g.user,
            start=week_start,
            end=week_end,
        )
    )


@bp.get("/reports/monthly")
@auth_required
def monthly_report():
    month = request.args.get("month", "")

    try:
        month_start, month_end = month_bounds(month)
    except ValueError as exc:
        raise ApiError(422, "invalid_month", str(exc))

    return jsonify(
        build_period_report(
            user=g.user,
            start=month_start,
            end=month_end,
        )
    )
