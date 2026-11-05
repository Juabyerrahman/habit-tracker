from datetime import timedelta

from flask import Blueprint, g, jsonify, request

from app.auth.decorators import auth_required
from app.errors import ApiError
from app.extensions import db
from app.models import Task
from app.routes._helpers import next_sort_order, owned_or_404
from app.schemas import load
from app.schemas.task import TaskCarrySchema, TaskCreateSchema, TaskReorderSchema, TaskUpdateSchema
from app.utils.dates import parse_day
from app.utils.time import utcnow

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")
# Deliberately imports nothing from habits: task changes can never touch habit history.


def _day_tasks(day):
    return (
        Task.query.filter(Task.user_id == g.user.id, Task.date == day, Task.deleted_at.is_(None))
        .order_by(Task.sort_order, Task.created_at)
        .all()
    )


@bp.get("")
@auth_required
def list_tasks():
    day = parse_day(request.args.get("date", ""), "date")
    tasks = _day_tasks(day)
    done = sum(1 for t in tasks if t.is_completed)
    return jsonify(
        {
            "date": day.isoformat(),
            "tasks": [t.to_dict() for t in tasks],
            "completed": done,
            "total": len(tasks),
            "completion_rate": round(done / len(tasks) * 100, 1) if tasks else None,  # None, never a fake 0%/100%
        }
    )


@bp.post("")
@auth_required
def create_task():
    data = load(TaskCreateSchema(), request.get_json(silent=True))
    task = Task(
        user_id=g.user.id,
        title=data["title"],
        notes=data["notes"],
        date=data["date"],
        sort_order=next_sort_order(Task, Task.date == data["date"], Task.deleted_at.is_(None)),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({"task": task.to_dict()}), 201


@bp.patch("/<task_id>")
@auth_required
def update_task(task_id):
    task = owned_or_404(Task, task_id)
    data = load(TaskUpdateSchema(), request.get_json(silent=True))
    if "is_completed" in data and data["is_completed"] != task.is_completed:
        task.is_completed = data["is_completed"]
        task.completed_at = utcnow() if task.is_completed else None
    data.pop("is_completed", None)
    if "date" in data and data["date"] != task.date:
        task.sort_order = next_sort_order(Task, Task.date == data["date"], Task.deleted_at.is_(None))
    for key, value in data.items():
        setattr(task, key, value)
    db.session.commit()
    return jsonify({"task": task.to_dict()})


@bp.delete("/<task_id>")
@auth_required
def delete_task(task_id):
    task = owned_or_404(Task, task_id)
    task.deleted_at = utcnow()  # soft delete keeps the record consistent for sync
    db.session.commit()
    return "", 204


@bp.post("/reorder")
@auth_required
def reorder_tasks():
    data = load(TaskReorderSchema(), request.get_json(silent=True))
    by_id = {t.id: t for t in _day_tasks(data["date"])}
    ids = data["ordered_ids"]
    if len(set(ids)) != len(ids) or not set(ids) <= by_id.keys():
        raise ApiError(422, "invalid_ids", "ordered_ids must be unique tasks that belong to that date.")
    rest = [t for t in by_id.values() if t.id not in set(ids)]
    for position, task in enumerate([by_id[i] for i in ids] + rest):
        task.sort_order = position
    db.session.commit()
    return jsonify({"tasks": [t.to_dict() for t in _day_tasks(data["date"])]})


@bp.post("/<task_id>/carry-forward")
@auth_required
def carry_forward(task_id):
    """Manually copy an unfinished task to another date. The original stays as history."""
    task = owned_or_404(Task, task_id)
    data = load(TaskCarrySchema(), request.get_json(silent=True))
    target = data["date"]
    if task.is_completed:
        raise ApiError(409, "task_completed", "Only unfinished tasks can be carried forward.")
    if target == task.date:
        raise ApiError(422, "same_date", "Choose a different date.")
    existing = Task.query.filter_by(user_id=g.user.id, carried_from_task_id=task.id, date=target, deleted_at=None).first()
    if existing:  # idempotent: no duplicates on retry
        return jsonify({"task": existing.to_dict()}), 200
    copy = Task(
        user_id=g.user.id,
        title=task.title,
        notes=task.notes,
        date=target,
        carried_from_task_id=task.id,
        sort_order=next_sort_order(Task, Task.date == target, Task.deleted_at.is_(None)),
    )
    db.session.add(copy)
    db.session.commit()
    return jsonify({"task": copy.to_dict()}), 201
