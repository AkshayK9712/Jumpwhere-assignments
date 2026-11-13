from sqlalchemy import func, select

from app.models import ActivityLog, SensorReading

BASE = "/api/v1"


def payload(**overrides):
    body = {"title": "Boiler", "category": "temperature", "metadata": {"factory": "Plant A", "unit": "C"}}
    body.update(overrides)
    return body


def create(client, headers, **overrides):
    r = client.post(f"{BASE}/sensors", json=payload(**overrides), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- create / validation ----------
def test_create_sensor(client, make_user, bearer):
    user = make_user("user")
    r = client.post(f"{BASE}/sensors", json=payload(priority="high"), headers=bearer(user))
    assert r.status_code == 201
    body = r.json()
    assert body["user_id"] == user.id
    assert body["status"] == "active" and body["priority"] == "high"
    assert body["metadata"] == {"factory": "Plant A", "unit": "C"}  # exposed as "metadata"
    assert "meta" not in body


def test_create_requires_login(client):
    assert client.post(f"{BASE}/sensors", json=payload()).status_code == 401


def test_guest_cannot_create(client, make_user, bearer):
    assert client.post(f"{BASE}/sensors", json=payload(), headers=bearer(make_user("guest"))).status_code == 403


def test_validation_errors(client, make_user, bearer):
    h = bearer(make_user("user"))
    assert client.post(f"{BASE}/sensors", json=payload(category="banana"), headers=h).status_code == 422
    assert client.post(f"{BASE}/sensors", json=payload(title=""), headers=h).status_code == 422
    assert client.post(f"{BASE}/sensors", json=payload(title="<b></b>"), headers=h).status_code == 422
    bad_thresholds = payload(metadata={"thresholds": {"min": 10, "max": 5}})
    assert client.post(f"{BASE}/sensors", json=bad_thresholds, headers=h).status_code == 422
    assert client.post(f"{BASE}/sensors", json={"title": "x"}, headers=h).status_code == 422  # category missing


def test_text_is_sanitized(client, make_user, bearer):
    h = bearer(make_user("user"))
    s = create(client, h, title="<script>alert(1)</script>Boiler", description="<i>hot</i> line",
               metadata={"location": "<b>Room 1</b>"})
    assert s["title"] == "alert(1)Boiler"
    assert s["description"] == "hot line"
    assert s["metadata"]["location"] == "Room 1"


# ---------- visibility ----------
def test_user_sees_only_own_sensors_but_admin_and_guest_see_all(client, make_user, bearer):
    a, b = make_user("user"), make_user("user")
    admin, guest = make_user("admin"), make_user("guest")
    create(client, bearer(a), title="A1")
    create(client, bearer(a), title="A2")
    create(client, bearer(b), title="B1")

    assert client.get(f"{BASE}/sensors", headers=bearer(a)).json()["total"] == 2
    assert client.get(f"{BASE}/sensors", headers=bearer(b)).json()["total"] == 1
    assert client.get(f"{BASE}/sensors", headers=bearer(admin)).json()["total"] == 3
    assert client.get(f"{BASE}/sensors", headers=bearer(guest)).json()["total"] == 3


def test_user_gets_404_for_someone_elses_sensor(client, make_user, bearer):
    a, b, admin = make_user("user"), make_user("user"), make_user("admin")
    sensor = create(client, bearer(a))
    assert client.get(f"{BASE}/sensors/{sensor['id']}", headers=bearer(b)).status_code == 404
    assert client.patch(f"{BASE}/sensors/{sensor['id']}", json={"title": "x"}, headers=bearer(b)).status_code == 404
    assert client.delete(f"{BASE}/sensors/{sensor['id']}", headers=bearer(b)).status_code == 404
    assert client.get(f"{BASE}/sensors/{sensor['id']}", headers=bearer(admin)).status_code == 200


def test_guest_cannot_modify(client, make_user, bearer):
    owner, guest = make_user("user"), make_user("guest")
    sensor = create(client, bearer(owner))
    assert client.patch(f"{BASE}/sensors/{sensor['id']}", json={"title": "x"}, headers=bearer(guest)).status_code == 403
    assert client.delete(f"{BASE}/sensors/{sensor['id']}", headers=bearer(guest)).status_code == 403


# ---------- list: pagination, filters, sorting ----------
def test_pagination(client, make_user, bearer):
    h = bearer(make_user("user"))
    for i in range(3):
        create(client, h, title=f"S{i}")
    p1 = client.get(f"{BASE}/sensors", params={"page_size": 2}, headers=h).json()
    p2 = client.get(f"{BASE}/sensors", params={"page_size": 2, "page": 2}, headers=h).json()
    assert (p1["total"], p1["pages"], len(p1["items"])) == (3, 2, 2)
    assert len(p2["items"]) == 1
    assert {s["id"] for s in p1["items"]}.isdisjoint({s["id"] for s in p2["items"]})


def test_page_size_limit(client, make_user, bearer):
    h = bearer(make_user("user"))
    assert client.get(f"{BASE}/sensors", params={"page_size": 101}, headers=h).status_code == 422
    assert client.get(f"{BASE}/sensors", params={"page": 0}, headers=h).status_code == 422


def test_filters(client, make_user, bearer):
    h = bearer(make_user("user"))
    create(client, h, title="Hot", category="temperature", status="active", priority="high")
    create(client, h, title="Press", category="pressure", status="faulty", priority="low")
    create(client, h, title="Damp", category="humidity", status="inactive", priority="low")

    def total(**params):
        return client.get(f"{BASE}/sensors", params=params, headers=h).json()["total"]

    assert total(category="pressure") == 1
    assert total(status="faulty") == 1
    assert total(priority="low") == 2
    assert total(q="ham") == 0 and total(q="ho") == 1
    assert total(category="pressure", status="active") == 0


def test_search_treats_percent_literally(client, make_user, bearer):
    h = bearer(make_user("user"))
    create(client, h, title="100% load")
    create(client, h, title="normal")
    found = client.get(f"{BASE}/sensors", params={"q": "%"}, headers=h).json()
    assert [s["title"] for s in found["items"]] == ["100% load"]


def test_sorting(client, make_user, bearer):
    h = bearer(make_user("user"))
    create(client, h, title="b", priority="high")
    create(client, h, title="a", priority="low")
    create(client, h, title="c", priority="critical")

    def titles(sort):
        return [s["title"] for s in client.get(f"{BASE}/sensors", params={"sort": sort}, headers=h).json()["items"]]

    assert titles("title") == ["a", "b", "c"]
    assert titles("-title") == ["c", "b", "a"]
    assert titles("-priority") == ["c", "b", "a"]  # critical, high, low
    assert client.get(f"{BASE}/sensors", params={"sort": "bogus"}, headers=h).status_code == 422


# ---------- update / delete ----------
def test_put_replaces_sensor(client, make_user, bearer):
    h = bearer(make_user("user"))
    s = create(client, h, title="Old", priority="low")
    r = client.put(f"{BASE}/sensors/{s['id']}", json=payload(title="New", category="pressure"), headers=h)
    assert r.status_code == 200
    assert r.json()["title"] == "New" and r.json()["priority"] == "medium"  # PUT resets omitted fields to defaults


def test_patch_changes_only_given_fields(client, make_user, bearer):
    h = bearer(make_user("user"))
    s = create(client, h, title="Keep", priority="high")
    r = client.patch(f"{BASE}/sensors/{s['id']}", json={"status": "faulty"}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "faulty" and body["title"] == "Keep" and body["priority"] == "high"
    assert body["metadata"] == s["metadata"]


def test_patch_replaces_metadata_and_rejects_nulls(client, make_user, bearer):
    h = bearer(make_user("user"))
    s = create(client, h)
    r = client.patch(f"{BASE}/sensors/{s['id']}", json={"metadata": {"unit": "bar"}}, headers=h)
    assert r.json()["metadata"] == {"unit": "bar"}
    assert client.patch(f"{BASE}/sensors/{s['id']}", json={"title": None}, headers=h).status_code == 422
    assert client.patch(f"{BASE}/sensors/{s['id']}", json={"description": None}, headers=h).status_code == 200


def test_if_unmodified_since_conflict(client, make_user, bearer):
    h = bearer(make_user("user"))
    s = create(client, h)
    url = f"{BASE}/sensors/{s['id']}"
    stale = client.patch(url, json={"title": "X"}, headers={**h, "If-Unmodified-Since": "2000-01-01T00:00:00Z"})
    assert stale.status_code == 409
    fresh = client.patch(url, json={"title": "X"}, headers={**h, "If-Unmodified-Since": "2100-01-01T00:00:00Z"})
    assert fresh.status_code == 200


def test_delete_sensor_removes_its_readings(client, make_user, bearer, db_session):
    h = bearer(make_user("user"))
    s = create(client, h)
    assert client.post(f"{BASE}/sensors/{s['id']}/readings", json={"value": 1.5}, headers=h).status_code == 201

    assert client.delete(f"{BASE}/sensors/{s['id']}", headers=h).status_code == 204
    assert client.get(f"{BASE}/sensors/{s['id']}", headers=h).status_code == 404
    assert db_session.scalar(select(func.count(SensorReading.id))) == 0


def test_get_unknown_sensor_is_404(client, make_user, bearer):
    assert client.get(f"{BASE}/sensors/9999", headers=bearer(make_user("user"))).status_code == 404


# ---------- bulk ----------
def test_bulk_create(client, make_user, bearer):
    h = bearer(make_user("user"))
    r = client.post(f"{BASE}/sensors/bulk", json={"items": [payload(title="A"), payload(title="B")]}, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["processed"] == 2 and body["failed"] == 0 and len(body["ids"]) == 2
    assert client.get(f"{BASE}/sensors", headers=h).json()["total"] == 2


def test_bulk_create_is_all_or_nothing(client, make_user, bearer):
    h = bearer(make_user("user"))
    r = client.post(f"{BASE}/sensors/bulk", json={"items": [payload(title="OK"), payload(category="nope")]}, headers=h)
    assert r.status_code == 422
    assert client.get(f"{BASE}/sensors", headers=h).json()["total"] == 0


def test_bulk_create_limits(client, make_user, bearer):
    h = bearer(make_user("user"))
    assert client.post(f"{BASE}/sensors/bulk", json={"items": []}, headers=h).status_code == 422
    too_many = {"items": [payload(title=f"S{i}") for i in range(101)]}
    assert client.post(f"{BASE}/sensors/bulk", json=too_many, headers=h).status_code == 422


def test_bulk_delete_is_partial(client, make_user, bearer):
    mine, theirs = make_user("user"), make_user("user")
    own = create(client, bearer(mine))
    foreign = create(client, bearer(theirs))
    r = client.request("DELETE", f"{BASE}/sensors/bulk", json={"ids": [own["id"], foreign["id"], 9999]}, headers=bearer(mine))
    assert r.status_code == 200
    body = r.json()
    assert body["processed"] == 1 and body["failed"] == 2 and len(body["errors"]) == 2
    assert client.get(f"{BASE}/sensors/{foreign['id']}", headers=bearer(theirs)).status_code == 200


# ---------- audit trail ----------
def test_sensor_changes_are_audited(client, make_user, bearer, db_session):
    user = make_user("user")
    h = bearer(user)
    s = create(client, h)
    client.patch(f"{BASE}/sensors/{s['id']}", json={"title": "Renamed"}, headers=h)
    client.delete(f"{BASE}/sensors/{s['id']}", headers=h)
    rows = db_session.scalars(select(ActivityLog).where(ActivityLog.entity_type == "sensor")).all()
    assert {r.action for r in rows} == {"sensor.create", "sensor.update", "sensor.delete"}
    assert all(r.user_id == user.id for r in rows)
