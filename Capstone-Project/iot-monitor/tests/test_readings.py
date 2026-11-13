from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import ActivityLog

BASE = "/api/v1"


def iso(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def make_sensor(client, headers):
    r = client.post(f"{BASE}/sensors", json={"title": "S", "category": "temperature"}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_create_reading_defaults_to_now(client, make_user, bearer):
    h = bearer(make_user("user"))
    sid = make_sensor(client, h)
    r = client.post(f"{BASE}/sensors/{sid}/readings", json={"value": 71.5}, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["sensor_id"] == sid and body["value"] == 71.5 and body["recorded_at"]


def test_reading_validation(client, make_user, bearer):
    h = bearer(make_user("user"))
    sid = make_sensor(client, h)
    url = f"{BASE}/sensors/{sid}/readings"
    assert client.post(url, json={"value": "hot"}, headers=h).status_code == 422
    assert client.post(url, json={}, headers=h).status_code == 422
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert client.post(url, json={"value": 1, "recorded_at": future}, headers=h).status_code == 422


def test_list_readings_newest_first_with_filters(client, make_user, bearer):
    h = bearer(make_user("user"))
    sid = make_sensor(client, h)
    url = f"{BASE}/sensors/{sid}/readings"
    for value, minutes_ago in [(1.0, 180), (2.0, 120), (3.0, 60)]:
        assert client.post(url, json={"value": value, "recorded_at": iso(minutes_ago)}, headers=h).status_code == 201

    allr = client.get(url, headers=h).json()
    assert [r["value"] for r in allr] == [3.0, 2.0, 1.0]

    recent = client.get(url, params={"from": iso(150)}, headers=h).json()
    assert [r["value"] for r in recent] == [3.0, 2.0]

    window = client.get(url, params={"from": iso(150), "to": iso(90)}, headers=h).json()
    assert [r["value"] for r in window] == [2.0]

    assert len(client.get(url, params={"limit": 1}, headers=h).json()) == 1
    assert client.get(url, params={"limit": 0}, headers=h).status_code == 422
    assert client.get(url, params={"from": iso(10), "to": iso(100)}, headers=h).status_code == 422


def test_bulk_readings(client, make_user, bearer, db_session):
    user = make_user("user")
    h = bearer(user)
    sid = make_sensor(client, h)
    items = [{"value": float(i), "recorded_at": iso(60 - i)} for i in range(3)]
    r = client.post(f"{BASE}/sensors/{sid}/readings/bulk", json={"items": items}, headers=h)
    assert r.status_code == 201 and r.json()["processed"] == 3
    assert len(client.get(f"{BASE}/sensors/{sid}/readings", headers=h).json()) == 3
    actions = set(db_session.scalars(select(ActivityLog.action)))
    assert "reading.bulk_create" in actions


def test_bulk_readings_limits(client, make_user, bearer):
    h = bearer(make_user("user"))
    sid = make_sensor(client, h)
    url = f"{BASE}/sensors/{sid}/readings/bulk"
    assert client.post(url, json={"items": []}, headers=h).status_code == 422
    assert client.post(url, json={"items": [{"value": 1}] * 1001}, headers=h).status_code == 422


def test_guest_can_read_but_not_write(client, make_user, bearer):
    owner, guest = make_user("user"), make_user("guest")
    sid = make_sensor(client, bearer(owner))
    url = f"{BASE}/sensors/{sid}/readings"
    assert client.post(url, json={"value": 1}, headers=bearer(guest)).status_code == 403
    assert client.get(url, headers=bearer(guest)).status_code == 200


def test_user_cannot_touch_readings_of_others_sensor(client, make_user, bearer):
    owner, other = make_user("user"), make_user("user")
    sid = make_sensor(client, bearer(owner))
    url = f"{BASE}/sensors/{sid}/readings"
    assert client.get(url, headers=bearer(other)).status_code == 404
    assert client.post(url, json={"value": 1}, headers=bearer(other)).status_code == 404


def test_readings_of_unknown_sensor_is_404(client, make_user, bearer):
    assert client.get(f"{BASE}/sensors/9999/readings", headers=bearer(make_user("user"))).status_code == 404
