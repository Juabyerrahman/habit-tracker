
from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import re

from app.models import (
    Habit,
    HabitArchivePeriod,
    HabitCompletion,
    HabitScheduleVersion,
    Task,
)



def local_today(user) -> date:
    """Return today's date in the user's timezone."""
    return datetime.now(ZoneInfo(user.timezone)).date()





def date_range(start: date, end: date):
    """Yield every calendar date, inclusive."""
    current = start

    while current <= end:
        yield current
        current += timedelta(days=1)


def utc_to_local_date(value: datetime, timezone_name: str) -> date:
    """Convert a naive-UTC database timestamp to the user's local date."""
    utc_value = value.replace(tzinfo=timezone.utc)
    return utc_value.astimezone(ZoneInfo(timezone_name)).date()


def get_schedule_versions(habit: Habit) -> list[HabitScheduleVersion]:
    """Load all schedule versions once for a habit."""
    return (
        HabitScheduleVersion.query
        .filter_by(habit_id=habit.id)
        .order_by(HabitScheduleVersion.effective_from)
        .all()
    )


def schedule_mask_for_day(
    habit: Habit,
    day: date,
    versions: list[HabitScheduleVersion] | None = None,
) -> int:
    """Find the schedule version effective on a particular date."""
    if versions is None:
        versions = get_schedule_versions(habit)

    effective_mask = habit.schedule_mask

    for version in versions:
        if version.effective_from > day:
            break
        effective_mask = version.schedule_mask

    return effective_mask


def is_scheduled_on(
    habit: Habit,
    day: date,
    versions: list[HabitScheduleVersion] | None = None,
) -> bool:
    """Check whether a habit was scheduled on a particular weekday."""
    mask = schedule_mask_for_day(habit, day, versions)
    return bool(mask & (1 << day.weekday()))


def get_archive_periods(habit: Habit):
    """Load all archive periods for a habit."""
    return (
        HabitArchivePeriod.query
        .filter_by(habit_id=habit.id)
        .order_by(HabitArchivePeriod.archived_from)
        .all()
    )


def is_archived_on(
    day: date,
    periods: list[HabitArchivePeriod],
    timezone_name: str,
) -> bool:
    """Check whether an archive period overlaps any part of a local calendar day."""
    zone = ZoneInfo(timezone_name)

    local_start = datetime.combine(day, time.min, tzinfo=zone)
    local_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)

    day_start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    day_end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)

    for period in periods:
        period_end = period.restored_at

        overlaps = (
            period.archived_from < day_end_utc
            and (period_end is None or period_end > day_start_utc)
        )

        if overlaps:
            return True

    return False

def get_scheduled_completion_dates(habit: Habit) -> set[date]:
    """Return completed dates, excluding deleted and bonus completions."""
    rows = (
        HabitCompletion.query
        .filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.deleted_at.is_(None),
            HabitCompletion.is_bonus.is_(False),
        )
        .all()
    )

    return {row.date for row in rows}


def calculate_streaks(
    habit: Habit,
    today: date,
    timezone_name: str,
    completion_dates: set[date] | None = None,
    archive_periods: list[HabitArchivePeriod] | None = None,
) -> dict:
    """
    Calculate current and longest streaks.

    Rest days and archived calendar days are skipped.
    An incomplete scheduled day today does not prematurely break
    the current streak.
    """
    if completion_dates is None:
        completion_dates = get_scheduled_completion_dates(habit)

    if archive_periods is None:
        archive_periods = get_archive_periods(habit)
    versions= get_schedule_versions(habit)

    def ignored(day: date) -> bool:
        return (
            day < habit.start_date
            or is_archived_on(day, archive_periods, timezone_name)
            or not is_scheduled_on(habit, day, versions)
        )

    # Calculate longest streak across all historical dates.
    longest = 0
    running = 0

    for day in date_range(habit.start_date, today):
        if ignored(day):
            continue

        if day in completion_dates:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    # Calculate current streak, allowing today to remain pending.
    current = 0
    cursor = today

    if (
        cursor >= habit.start_date
        and not ignored(cursor)
        and cursor not in completion_dates
    ):
        cursor -= timedelta(days=1)

    while cursor >= habit.start_date:
        if ignored(cursor):
            cursor -= timedelta(days=1)
            continue

        if cursor in completion_dates:
            current += 1
            cursor -= timedelta(days=1)
        else:
            break

    return {
        "current": current,
        "longest": longest,
    }

def calculate_habit_performance(
    habit: Habit,
    start: date,
    end: date,
    today: date,
    timezone_name: str,
    completion_dates: set[date] | None = None,
    archive_periods: list[HabitArchivePeriod] | None = None,
) -> dict:
    """Calculate scheduled completion performance for one habit."""
    if completion_dates is None:
        completion_dates = get_scheduled_completion_dates(habit)

    if archive_periods is None:
        archive_periods = get_archive_periods(habit)

    versions = get_schedule_versions(habit)

    scheduled = 0
    completed = 0
    missed = 0
    pending = 0

    for day in date_range(max(start, habit.start_date), min(end, today)):
        if is_archived_on(day, archive_periods, timezone_name):
            continue

        if not is_scheduled_on(habit, day,versions):
            continue

        scheduled += 1

        if day in completion_dates:
            completed += 1
        elif day == today:
            pending += 1
        else:
            missed += 1

    rate = round(completed / scheduled * 100, 1) if scheduled else None

    return {
        "habit_id": habit.id,
        "habit_name": habit.name,
        "scheduled_days": scheduled,
        "completed_days": completed,
        "missed_days": missed,
        "pending_days": pending,
        "completion_rate": rate,
    }

def calculate_task_performance(
    user_id: str,
    start: date,
    end: date,
) -> dict:
    """Calculate task performance within a date range."""
    tasks = (
        Task.query
        .filter(
            Task.user_id == user_id,
            Task.date >= start,
            Task.date <= end,
            Task.deleted_at.is_(None),
        )
        .all()
    )

    total = len(tasks)
    completed = sum(1 for task in tasks if task.is_completed)
    pending = total - completed

    carried_forward = sum(
        1 for task in tasks
        if task.carried_from_task_id is not None
    )

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "carried_forward": carried_forward,
        "completion_rate": (
            round(completed / total * 100, 1)
            if total else None
        ),
    }

def build_monthly_habit_grid(
    habit: Habit,
    month_start: date,
    month_end: date,
    today: date,
    timezone_name: str,
) -> dict:
    """Build daily status information for one habit in a month."""

    completions = (
        HabitCompletion.query
        .filter(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.date >= month_start,
            HabitCompletion.date <= month_end,
            HabitCompletion.deleted_at.is_(None),
        )
        .all()
    )

    completion_by_date = {
        row.date: row.is_bonus
        for row in completions
    }

    archive_periods = get_archive_periods(habit)
    versions = get_schedule_versions(habit)

    days = []

    for day in date_range(month_start, month_end):
        is_bonus = completion_by_date.get(day)
        is_completed = day in completion_by_date

        if day < habit.start_date:
            status = "before_start"

        elif day > today:
            status = "future"

        elif is_archived_on(day, archive_periods, timezone_name):
            status = "completed" if is_completed and not is_bonus else "archived"

        elif is_bonus:
            status = "bonus"

        elif is_completed:
            status = "completed"

        elif not is_scheduled_on(habit, day,versions):
            status = "rest"

        elif day == today:
            status = "pending"

        else:
            status = "missed"

        days.append({
            "date": day.isoformat(),
            "weekday": day.weekday(),
            "scheduled": is_scheduled_on(habit, day,versions),
            "completed": is_completed,
            "is_bonus": bool(is_bonus),
            "status": status,
        })

    return {
        "habit_id": habit.id,
        "habit_name": habit.name,
        "days": days,
    }
def month_bounds(month: str) -> tuple[date, date]:
    """Return the first and last dates of a YYYY-MM month."""
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("month must use YYYY-MM format")

    year, month_number = map(int, month.split("-"))
    first = date(year, month_number, 1)
    last = date(year, month_number, monthrange(year, month_number)[1])

    return first, last
def build_period_report(user, start, end):
    """Build a weekly or monthly progress report dynamically."""

    today = local_today(user)
    report_end = min(end, today)

    habits = []
    total_scheduled = 0
    total_completed = 0
    daily_data = []

    # Include historical habits, even if they are now archived.
    if report_end >= start:
        habits = (
            Habit.query
            .filter(
                Habit.user_id == user.id,
                Habit.start_date <= report_end,
            )
            .order_by(Habit.sort_order, Habit.created_at)
            .all()
        )

    habit_reports = []
    habit_contexts = []

    for habit in habits:
        versions = get_schedule_versions(habit)
        archive_periods = get_archive_periods(habit)
        completion_dates = get_scheduled_completion_dates(habit)

        scheduled = 0
        completed = 0
        missed = 0
        pending = 0

        for day in date_range(max(start, habit.start_date), report_end):
            if is_archived_on(day, archive_periods, user.timezone):
                continue

            if not is_scheduled_on(habit,day, versions):
                continue

            scheduled += 1

            if day in completion_dates:
                completed += 1
            elif day < today:
                missed += 1
            else:
                pending += 1

        rate = round(completed / scheduled * 100, 1) if scheduled else None

        habit_reports.append({
            "habit_id": habit.id,
            "habit_name": habit.name,
            "scheduled_days": scheduled,
            "completed_days": completed,
            "missed_days": missed,
            "pending_days": pending,
            "completion_rate": rate,
        })

        habit_contexts.append({
            "habit": habit,
            "versions": versions,
            "archive_periods": archive_periods,
            "completion_dates": completion_dates,
        })

        total_scheduled += scheduled
        total_completed += completed

    # Load tasks for the report period.
    tasks = []
    if report_end >= start:
        tasks = (
            Task.query
            .filter(
                Task.user_id == user.id,
                Task.date >= start,
                Task.date <= report_end,
                Task.deleted_at.is_(None),
            )
            .all()
        )

    tasks_by_date = {}
    for task in tasks:
        tasks_by_date.setdefault(task.date, []).append(task)

    task_total = len(tasks)
    task_completed = sum(1 for task in tasks if task.is_completed)
    task_pending = task_total - task_completed
    task_carried_forward = sum(
        1 for task in tasks if task.carried_from_task_id is not None
    )

    # Build daily trends.
    for day in date_range(start, report_end):
        day_scheduled = 0
        day_completed = 0

        for context in habit_contexts:
            habit = context["habit"]

            if day < habit.start_date:
                continue

            if is_archived_on(
                day,
                context["archive_periods"],
                user.timezone,
            ):
                continue

            if not is_scheduled_on(habit,day, context["versions"]):
                continue

            day_scheduled += 1

            if day in context["completion_dates"]:
                day_completed += 1

        day_tasks = tasks_by_date.get(day, [])
        day_task_completed = sum(1 for task in day_tasks if task.is_completed)

        overall_total = day_scheduled + len(day_tasks)
        overall_completed = day_completed + day_task_completed

        daily_data.append({
            "date": day.isoformat(),
            "habits_scheduled": day_scheduled,
            "habits_completed": day_completed,
            "tasks_total": len(day_tasks),
            "tasks_completed": day_task_completed,
            "overall_total": overall_total,
            "overall_completed": overall_completed,
            "overall_completion_rate": (
                round(overall_completed / overall_total * 100, 1)
                if overall_total else None
            ),
        })

    # Rank habits only when they had scheduled days.
    ranked_habits = [
        habit for habit in habit_reports
        if habit["completion_rate"] is not None
    ]

    strongest = sorted(
        ranked_habits,
        key=lambda item: (-item["completion_rate"], item["habit_name"]),
    )[:3]

    weakest = sorted(
        ranked_habits,
        key=lambda item: (item["completion_rate"], item["habit_name"]),
    )[:3]

    eligible_days = [
        day for day in daily_data
        if day["overall_completion_rate"] is not None
    ]

    best_day = (
        max(eligible_days, key=lambda item: item["overall_completion_rate"])
        if eligible_days else None
    )

    worst_day = (
        min(eligible_days, key=lambda item: item["overall_completion_rate"])
        if eligible_days else None
    )

    overall_total = total_scheduled + task_total
    overall_completed = total_completed + task_completed

    return {
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "through": report_end.isoformat() if report_end >= start else None,
        },
        "overview": {
            "habit_scheduled": total_scheduled,
            "habit_completed": total_completed,
            "habit_missed": sum(h["missed_days"] for h in habit_reports),
            "habit_pending": sum(h["pending_days"] for h in habit_reports),
            "habit_completion_rate": (
                round(total_completed / total_scheduled * 100, 1)
                if total_scheduled else None
            ),
            "task_total": task_total,
            "task_completed": task_completed,
            "task_pending": task_pending,
            "task_carried_forward": task_carried_forward,
            "task_completion_rate": (
                round(task_completed / task_total * 100, 1)
                if task_total else None
            ),
            "overall_total": overall_total,
            "overall_completed": overall_completed,
            "overall_completion_rate": (
                round(overall_completed / overall_total * 100, 1)
                if overall_total else None
            ),
        },
        "habits": habit_reports,
        "strongest_habits": strongest,
        "weakest_habits": weakest,
        "daily_trends": daily_data,
        "best_day": best_day,
        "worst_day": worst_day,
    }
