from datetime import date, timedelta

from app.models import HabitCompletion, HabitScheduleVersion
from app.utils.time import today_in
from tests.conftest import signup


def today():
    return today_in("UTC")


def make_habit(client, headers, **extra):
    body = {"name": "Exercise", "start_date": (today() - timedelta(days=10)).isoformat(), **extra}
    r = client.post("/api/habits", headers=headers, json=body)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["habit"]


def test_create_defaults_and_validation(client, auth):
    h = client.post("/api/habits", headers=auth, json={"name": "Read"}).get_json()["habit"]
    assert h["start_date"] == today().isoformat() and h["schedule"] == [0, 1, 2, 3, 4, 5, 6]
    for bad in ({"name": ""}, {"name": "x" * 101}, {"name": "x", "schedule": []}, {"name": "x", "schedule": [7]},
                {"name": "x", "start_date": "2026-13-40"}, {"name": "x", "user_id": "abc"}):
        assert client.post("/api/habits", headers=auth, json=bad).status_code == 422


def test_schedule_roundtrip_and_update(client, auth):
    h = make_habit(client, auth, schedule=[0, 2, 4])
    assert h["schedule"] == [0, 2, 4]
    r = client.patch(f"/api/habits/{h['id']}", headers=auth, json={"name": "Gym", "schedule": [5, 6]})
    assert r.get_json()["habit"]["name"] == "Gym" and r.get_json()["habit"]["schedule"] == [5, 6]


def test_completion_is_idempotent_and_can_be_cleared(client, auth):
    h = make_habit(client, auth)
    d = (today() - timedelta(days=2)).isoformat()
    url = f"/api/habits/{h['id']}/completions/{d}"
    assert client.put(url, headers=auth).status_code == 200
    assert client.put(url, headers=auth).status_code == 200  # no duplicate
    assert HabitCompletion.query.count() == 1
    rng = f"/api/habits/{h['id']}/completions?from={(today() - timedelta(days=9)).isoformat()}&to={today().isoformat()}"
    assert client.get(rng, headers=auth).get_json()["dates"] == [d]
    assert client.delete(url, headers=auth).get_json()["completed"] is False
    assert client.get(rng, headers=auth).get_json()["dates"] == []
    assert client.put(url, headers=auth).status_code == 200  # re-complete after un-check
    assert client.get(rng, headers=auth).get_json()["dates"] == [d]
    assert HabitCompletion.query.count() == 1


def test_future_and_pre_start_dates_rejected(client, auth):
    h = make_habit(client, auth)
    future = (today() + timedelta(days=1)).isoformat()
    before = (today() - timedelta(days=11)).isoformat()
    r = client.put(f"/api/habits/{h['id']}/completions/{future}", headers=auth)
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "future_date"
    r = client.put(f"/api/habits/{h['id']}/completions/{before}", headers=auth)
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "before_start_date"
    assert client.put(f"/api/habits/{h['id']}/completions/2026-02-30", headers=auth).status_code == 422
    assert client.put(f"/api/habits/{h['id']}/completions/20261104", headers=auth).status_code == 422


def test_today_uses_user_timezone(client):
    # Kiritimati (UTC+14) is often a calendar day ahead of UTC: 'today' there must be accepted.
    h = signup(client, "tz@example.com", timezone="Pacific/Kiritimati")
    local_today = today_in("Pacific/Kiritimati")
    habit = client.post("/api/habits", headers=h, json={"name": "x"}).get_json()["habit"]
    assert habit["start_date"] == local_today.isoformat()
    assert client.put(f"/api/habits/{habit['id']}/completions/{local_today}", headers=h).status_code == 200


def test_archive_keeps_history_and_is_read_only(client, auth):
    h = make_habit(client, auth)
    d = (today() - timedelta(days=1)).isoformat()
    client.put(f"/api/habits/{h['id']}/completions/{d}", headers=auth)
    assert client.post(f"/api/habits/{h['id']}/archive", headers=auth).status_code == 200

    assert client.get("/api/habits", headers=auth).get_json()["habits"] == []
    assert len(client.get("/api/habits?include_archived=true", headers=auth).get_json()["habits"]) == 1
    assert HabitCompletion.query.count() == 1  # history intact

    r = client.put(f"/api/habits/{h['id']}/completions/{today().isoformat()}", headers=auth)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "habit_archived"
    assert client.patch(f"/api/habits/{h['id']}", headers=auth, json={"name": "x"}).status_code == 409

    client.post(f"/api/habits/{h['id']}/restore", headers=auth)
    assert client.put(f"/api/habits/{h['id']}/completions/{today().isoformat()}", headers=auth).status_code == 200
    rng = f"from={(today() - timedelta(days=9)).isoformat()}&to={today().isoformat()}"
    assert len(client.get(f"/api/habits/{h['id']}/completions?{rng}", headers=auth).get_json()["dates"]) == 2


def test_start_date_cannot_move_past_existing_completion(client, auth):
    h = make_habit(client, auth)
    d = today() - timedelta(days=5)
    client.put(f"/api/habits/{h['id']}/completions/{d}", headers=auth)
    r = client.patch(f"/api/habits/{h['id']}", headers=auth, json={"start_date": (d + timedelta(days=1)).isoformat()})
    assert r.status_code == 422
    assert client.patch(f"/api/habits/{h['id']}", headers=auth, json={"start_date": d.isoformat()}).status_code == 200


def test_users_cannot_access_each_others_habits(app, client, auth):
    h = make_habit(client, auth)
    other = signup(app.test_client(), "b@example.com")
    c2 = app.test_client()
    d = today().isoformat()
    for method, url in [
        ("get", f"/api/habits/{h['id']}"),
        ("patch", f"/api/habits/{h['id']}"),
        ("post", f"/api/habits/{h['id']}/archive"),
        ("put", f"/api/habits/{h['id']}/completions/{d}"),
        ("delete", f"/api/habits/{h['id']}/completions/{d}"),
        ("get", f"/api/habits/{h['id']}/completions?from={d}&to={d}"),
    ]:
        r = getattr(c2, method)(url, headers=other, json={"name": "hack"} if method == "patch" else None)
        assert r.status_code == 404, (method, url)
    assert c2.get("/api/habits", headers=other).get_json()["habits"] == []
def test_create_habit_creates_initial_schedule_version(client, auth):
    h = make_habit(client, auth, schedule=[0, 2, 4])

    versions = HabitScheduleVersion.query.filter_by(
        habit_id=h["id"]
    ).all()

    assert len(versions) == 1
    assert versions[0].effective_from == today() - timedelta(days=10)
    assert versions[0].schedule_mask == 21


def test_same_day_schedule_changes_update_existing_version(
    client, auth, monkeypatch
):
    h = make_habit(client, auth, schedule=[0, 2, 4])

    today_date = date(2026, 11, 4)
    monkeypatch.setattr(
        "app.routes.habits.today_in",
        lambda timezone: today_date,
    )

    url = f"/api/habits/{h['id']}"

    # First schedule change.
    r = client.patch(url, headers=auth, json={"schedule": [5, 6]})
    assert r.status_code == 200

    # Second change on the same day.
    r = client.patch(url, headers=auth, json={"schedule": [1, 3]})
    assert r.status_code == 200

    # Repeating the same schedule must not create another version.
    r = client.patch(url, headers=auth, json={"schedule": [1, 3]})
    assert r.status_code == 200

    versions = (
        HabitScheduleVersion.query
        .filter_by(habit_id=h["id"])
        .order_by(HabitScheduleVersion.effective_from)
        .all()
    )

    assert len(versions) == 2
    assert versions[0].schedule_mask == 21
    assert versions[1].effective_from == today_date
    assert versions[1].schedule_mask == 10


def test_schedule_changes_on_different_days_create_versions(
    client, auth, monkeypatch
):
    h = make_habit(client, auth, schedule=[0, 2, 4])
    url = f"/api/habits/{h['id']}"

    first_day = date(2026, 11, 4)
    second_day = date(2026, 11, 5)

    monkeypatch.setattr(
        "app.routes.habits.today_in",
        lambda timezone: first_day,
    )

    r = client.patch(url, headers=auth, json={"schedule": [5, 6]})
    assert r.status_code == 200

    monkeypatch.setattr(
        "app.routes.habits.today_in",
        lambda timezone: second_day,
    )

    r = client.patch(url, headers=auth, json={"schedule": [0, 6]})
    assert r.status_code == 200

    versions = (
        HabitScheduleVersion.query
        .filter_by(habit_id=h["id"])
        .order_by(HabitScheduleVersion.effective_from)
        .all()
    )

    assert len(versions) == 3
    assert versions[0].schedule_mask == 21
    assert versions[1].effective_from == first_day
    assert versions[1].schedule_mask == 96
    assert versions[2].effective_from == second_day
    assert versions[2].schedule_mask == 65


def test_moving_start_date_earlier_extends_initial_schedule(
    client, auth
):
    h = make_habit(client, auth, schedule=[0, 2, 4])

    new_start_date = today() - timedelta(days=15)

    r = client.patch(
        f"/api/habits/{h['id']}",
        headers=auth,
        json={"start_date": new_start_date.isoformat()},
    )

    assert r.status_code == 200

    versions = HabitScheduleVersion.query.filter_by(
        habit_id=h["id"]
    ).all()

    assert len(versions) == 1
    assert versions[0].effective_from == new_start_date
    assert versions[0].schedule_mask == 21