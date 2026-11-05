from datetime import date, timedelta

from app.models import Habit, HabitCompletion
from app.services.statistics import calculate_streaks
from app.utils.time import today_in
from app.extensions import db


def today():
    return today_in("UTC")


def create_habit(client, auth, schedule):
    start = today() - timedelta(days=10)

    response = client.post(
        "/api/habits",
        headers=auth,
        json={
            "name": "Statistics Test",
            "start_date": start.isoformat(),
            "schedule": schedule,
        },
    )

    assert response.status_code == 201
    return response.get_json()["habit"]


def complete_day(habit_id, user_id, day):
    completion = HabitCompletion(
        habit_id=habit_id,
        user_id=user_id,
        date=day,
        is_bonus=False,
    )


    db.session.add(completion)
    db.session.commit()


def test_streaks_skip_rest_days(client, auth):
    habit_data = create_habit(client, auth, schedule=[0, 2, 4])

    habit = db.session.get(Habit, habit_data["id"])

    # Use a fixed Wednesday so the test is independent of today's weekday.
    fixed_today = date(2026, 11, 4)

    # Scheduled days: Monday, Wednesday, Friday.
    completed_days = {
        date(2026, 11, 2),
        date(2026, 11, 4),
    }

    # Add historical completions.
    for day in completed_days:
        complete_day(habit.id, habit.user_id, day)

    result = calculate_streaks(
        habit=habit,
        today=fixed_today,
        timezone_name="UTC",
    )

    assert result["current"] == 2
    assert result["longest"] == 2
def test_streak_breaks_when_scheduled_day_is_missed(client, auth):
    habit_data = create_habit(client, auth, schedule=[0, 2, 4])
    habit = db.session.get(Habit, habit_data["id"])

    fixed_today = date(2026, 11, 5)

    # Monday was completed, but Wednesday (today) is not.
    complete_day(
        habit.id,
        habit.user_id,
        date(2026, 11, 2),
    )

    result = calculate_streaks(
        habit=habit,
        today=fixed_today,
        timezone_name="UTC",
    )

    assert result["current"] == 0
    assert result["longest"] == 1
def test_pending_today_preserves_current_streak(client, auth):
    habit_data = create_habit(client, auth, schedule=[0, 2, 4])
    habit = db.session.get(Habit, habit_data["id"])

    fixed_today = date(2026, 11, 4)

    # Monday completed; Wednesday is pending today.
    complete_day(
        habit.id,
        habit.user_id,
        date(2026, 11, 2),
    )

    result = calculate_streaks(
        habit=habit,
        today=fixed_today,
        timezone_name="UTC",
    )

    assert result["current"] == 1
    assert result["longest"] == 1
def test_longest_streak_survives_current_streak_break(client, auth):
    habit_data = create_habit(client, auth, schedule=[0, 2, 4])
    habit = db.session.get(Habit, habit_data["id"])

    fixed_today = date(2026, 11, 12)

    # Historical streak: Monday, Wednesday, Friday.
    # Current streak: Monday, November 9.
    completed_days = [
        date(2026, 11, 2),
        date(2026, 11, 4),
        date(2026, 11, 6),
        date(2026, 11, 9),
    ]

    for day in completed_days:
        complete_day(habit.id, habit.user_id, day)

    result = calculate_streaks(
        habit=habit,
        today=fixed_today,
        timezone_name="UTC",
    )

    assert result["current"] == 0
    assert result["longest"] == 4
def test_bonus_completion_does_not_increase_streak(client, auth):
    habit_data = create_habit(client, auth, schedule=[0, 2, 4])
    habit = db.session.get(Habit, habit_data["id"])

    fixed_today = date(2026, 11, 3)  # Thursday: rest day

    complete_day(
        habit.id,
        habit.user_id,
        date(2026, 11, 2),  # Monday: scheduled
    )

    bonus = HabitCompletion(
        habit_id=habit.id,
        user_id=habit.user_id,
        date=date(2026, 11, 3),
        is_bonus=True,
    )
    db.session.add(bonus)
    db.session.commit()

    result = calculate_streaks(
        habit=habit,
        today=fixed_today,
        timezone_name="UTC",
    )

    assert result["current"] == 1
    assert result["longest"] == 1
def test_weekly_report_returns_habit_performance(client, auth):
    habit_data = create_habit(client, auth, schedule=[0, 1, 2, 3, 4, 5, 6])
    habit = db.session.get(Habit, habit_data["id"])

    week_start = today() - timedelta(days=today().weekday())

    complete_day(
        habit.id,
        habit.user_id,
        week_start,
    )

    response = client.get(
        f"/api/reports/weekly?week_start={week_start.isoformat()}",
        headers=auth,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["period"]["start"] == week_start.isoformat()
    assert len(data["habits"]) == 1
    assert data["habits"][0]["habit_name"] == "Statistics Test"
    assert data["habits"][0]["completed_days"] == 1
    assert data["overview"]["habit_completed"] == 1


def test_weekly_report_rejects_non_monday(client, auth):
    response = client.get(
        "/api/reports/weekly?week_start=2026-11-04",
        headers=auth,
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "invalid_week_start"


def test_monthly_report_returns_valid_period(client, auth):
    response = client.get(
        "/api/reports/monthly?month=2026-11",
        headers=auth,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["period"]["start"] == "2026-11-01"
    assert data["period"]["end"] == "2026-11-30"
    assert "overview" in data
    assert "daily_trends" in data
