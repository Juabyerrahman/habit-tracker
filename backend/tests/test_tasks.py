from app.models import HabitCompletion
from tests.conftest import signup

D1, D2 = "2026-11-04", "2026-11-05"


def add(client, h, title, date=D1):
    r = client.post("/api/tasks", headers=h, json={"title": title, "date": date})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["task"]


def test_create_list_and_completion_rate(client, auth):
    empty = client.get(f"/api/tasks?date={D1}", headers=auth).get_json()
    assert empty["total"] == 0 and empty["completion_rate"] is None  # no misleading 0% / 100%
    a, b = add(client, auth, "Python lecture"), add(client, auth, "Assignment")
    client.patch(f"/api/tasks/{a['id']}", headers=auth, json={"is_completed": True})
    data = client.get(f"/api/tasks?date={D1}", headers=auth).get_json()
    assert [t["title"] for t in data["tasks"]] == ["Python lecture", "Assignment"]
    assert (data["completed"], data["total"], data["completion_rate"]) == (1, 2, 50.0)
    assert data["tasks"][0]["completed_at"] and data["tasks"][1]["completed_at"] is None
    r = client.patch(f"/api/tasks/{a['id']}", headers=auth, json={"is_completed": False})
    assert r.get_json()["task"]["completed_at"] is None


def test_validation(client, auth):
    for bad in ({"title": "", "date": D1}, {"title": "x"}, {"title": "x", "date": "tomorrow"}, {"title": "x", "date": D1, "is_completed": True}):
        assert client.post("/api/tasks", headers=auth, json=bad).status_code == 422
    assert client.get("/api/tasks", headers=auth).status_code == 422


def test_reorder(client, auth):
    a, b, c = (add(client, auth, t) for t in "abc")
    r = client.post("/api/tasks/reorder", headers=auth, json={"date": D1, "ordered_ids": [c["id"], a["id"]]})
    assert [t["title"] for t in r.get_json()["tasks"]] == ["c", "a", "b"]
    bad = client.post("/api/tasks/reorder", headers=auth, json={"date": D1, "ordered_ids": [a["id"], a["id"]]})
    assert bad.status_code == 422
    wrong_day = client.post("/api/tasks/reorder", headers=auth, json={"date": D2, "ordered_ids": [a["id"]]})
    assert wrong_day.status_code == 422


def test_soft_delete_and_move_date(client, auth):
    a = add(client, auth, "a")
    client.patch(f"/api/tasks/{a['id']}", headers=auth, json={"date": D2})
    assert client.get(f"/api/tasks?date={D1}", headers=auth).get_json()["total"] == 0
    assert client.get(f"/api/tasks?date={D2}", headers=auth).get_json()["total"] == 1
    assert client.delete(f"/api/tasks/{a['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/tasks?date={D2}", headers=auth).get_json()["total"] == 0
    assert client.patch(f"/api/tasks/{a['id']}", headers=auth, json={"title": "x"}).status_code == 404


def test_carry_forward(client, auth):
    a = add(client, auth, "RAG study")
    r = client.post(f"/api/tasks/{a['id']}/carry-forward", headers=auth, json={"date": D2})
    assert r.status_code == 201
    copy = r.get_json()["task"]
    assert copy["carried_from_task_id"] == a["id"] and copy["date"] == D2 and copy["is_completed"] is False
    again = client.post(f"/api/tasks/{a['id']}/carry-forward", headers=auth, json={"date": D2})
    assert again.status_code == 200 and again.get_json()["task"]["id"] == copy["id"]  # idempotent
    assert client.get(f"/api/tasks?date={D1}", headers=auth).get_json()["total"] == 1  # original kept as history
    assert client.post(f"/api/tasks/{a['id']}/carry-forward", headers=auth, json={"date": D1}).status_code == 422
    client.patch(f"/api/tasks/{a['id']}", headers=auth, json={"is_completed": True})
    assert client.post(f"/api/tasks/{a['id']}/carry-forward", headers=auth, json={"date": "2026-11-06"}).status_code == 409


def test_tasks_never_touch_habit_history(client, auth):
    h = client.post("/api/habits", headers=auth, json={"name": "x", "start_date": "2026-01-01"}).get_json()["habit"]
    client.put(f"/api/habits/{h['id']}/completions/2026-01-05", headers=auth)
    before = [(c.date, c.deleted_at) for c in HabitCompletion.query.all()]
    t = add(client, auth, "task")
    client.patch(f"/api/tasks/{t['id']}", headers=auth, json={"is_completed": True, "date": D2})
    client.delete(f"/api/tasks/{t['id']}", headers=auth)
    assert [(c.date, c.deleted_at) for c in HabitCompletion.query.all()] == before


def test_tasks_are_private(app, client, auth):
    t = add(client, auth, "secret")
    c2 = app.test_client()
    other = signup(c2, "b@example.com")
    assert c2.get(f"/api/tasks?date={D1}", headers=other).get_json()["total"] == 0
    assert c2.patch(f"/api/tasks/{t['id']}", headers=other, json={"title": "x"}).status_code == 404
    assert c2.delete(f"/api/tasks/{t['id']}", headers=other).status_code == 404
    assert c2.post(f"/api/tasks/{t['id']}/carry-forward", headers=other, json={"date": D2}).status_code == 404
