from datetime import datetime, timedelta, timezone

BASE = "/api/v1"
NOW = datetime.now(timezone.utc)


def ago(**kw):
    return NOW - timedelta(**kw)


def iso(dt):
    return dt.isoformat()


# ---------- summary ----------
def test_summary_counts_sensors_and_readings(client, make_user, make_sensor, bearer):
    user = make_user("user")
    make_sensor(user, "A", "temperature", "active", readings=[(ago(hours=2), 1.0), (ago(hours=1), 2.0)])
    make_sensor(user, "B", "pressure", "faulty", readings=[(ago(days=3), 5.0)])  # outside the default 24h
    make_sensor(user, "C", "temperature", "inactive")

    r = client.get(f"{BASE}/dashboard/summary", headers=bearer(user))
    assert r.status_code == 200
    body = r.json()
    assert body["total_sensors"] == 3
    assert (body["active_sensors"], body["inactive_sensors"], body["faulty_sensors"]) == (1, 1, 1)
    assert body["readings_in_range"] == 2
    assert body["sensors_by_category"] == {"temperature": 2, "pressure": 1}
    assert body["generated_at"] and body["range_from"] < body["range_to"]


def test_summary_range_and_category_filters(client, make_user, make_sensor, bearer):
    user = make_user("user")
    make_sensor(user, "A", "temperature", readings=[(ago(days=3), 1.0), (ago(hours=1), 2.0)])
    make_sensor(user, "B", "pressure", readings=[(ago(hours=1), 3.0)])
    h = bearer(user)

    week = client.get(f"{BASE}/dashboard/summary", params={"from": iso(ago(days=7))}, headers=h).json()
    assert week["readings_in_range"] == 3

    temp = client.get(f"{BASE}/dashboard/summary", params={"category": "temperature", "from": iso(ago(days=7))}, headers=h).json()
    assert temp["total_sensors"] == 1 and temp["readings_in_range"] == 2


def test_summary_respects_visibility(client, make_user, make_sensor, bearer):
    a, b, admin, guest = make_user("user"), make_user("user"), make_user("admin"), make_user("guest")
    make_sensor(a, "A1")
    make_sensor(a, "A2")
    make_sensor(b, "B1")

    def total(u):
        return client.get(f"{BASE}/dashboard/summary", headers=bearer(u)).json()["total_sensors"]

    assert (total(a), total(b), total(admin), total(guest)) == (2, 1, 3, 3)


def test_summary_requires_login_and_valid_range(client, make_user, bearer):
    assert client.get(f"{BASE}/dashboard/summary").status_code == 401
    h = bearer(make_user("user"))
    assert client.get(f"{BASE}/dashboard/summary", params={"from": iso(ago(hours=1)), "to": iso(ago(hours=2))}, headers=h).status_code == 422
    assert client.get(f"{BASE}/dashboard/summary", params={"from": iso(ago(days=400))}, headers=h).status_code == 422


def test_summary_with_no_sensors(client, make_user, bearer):
    body = client.get(f"{BASE}/dashboard/summary", headers=bearer(make_user("user"))).json()
    assert body["total_sensors"] == 0 and body["readings_in_range"] == 0 and body["sensors_by_category"] == {}


# ---------- time series ----------
def test_timeseries_hourly_buckets(client, make_user, make_sensor, bearer):
    user = make_user("user")
    base = NOW.replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)
    sensor = make_sensor(user, "Boiler", meta={"unit": "C", "thresholds": {"min": 60, "max": 90}}, readings=[
        (base + timedelta(minutes=5), 10.0), (base + timedelta(minutes=35), 30.0),   # hour 1: avg 20
        (base + timedelta(hours=1, minutes=10), 50.0),                               # hour 2
    ])
    r = client.get(f"{BASE}/dashboard/timeseries", params={"sensor_id": sensor.id, "from": iso(base - timedelta(hours=1)), "interval": "hour"},
                   headers=bearer(user))
    assert r.status_code == 200
    body = r.json()
    assert (body["title"], body["unit"], body["interval"]) == ("Boiler", "C", "hour")
    assert body["thresholds"] == {"min": 60.0, "max": 90.0}
    pts = body["points"]
    assert len(pts) == 2
    assert (pts[0]["count"], pts[0]["avg"], pts[0]["min"], pts[0]["max"]) == (2, 20.0, 10.0, 30.0)
    assert pts[1]["avg"] == 50.0
    assert pts[0]["bucket"] < pts[1]["bucket"]


def test_timeseries_minute_and_day_intervals(client, make_user, make_sensor, bearer):
    user = make_user("user")
    sensor = make_sensor(user, readings=[(ago(minutes=3), 1.0), (ago(minutes=2), 2.0), (ago(minutes=1), 3.0)])
    h = bearer(user)
    minute = client.get(f"{BASE}/dashboard/timeseries", params={"sensor_id": sensor.id, "from": iso(ago(minutes=10)), "interval": "minute"}, headers=h).json()
    assert len(minute["points"]) >= 3
    day = client.get(f"{BASE}/dashboard/timeseries", params={"sensor_id": sensor.id, "interval": "day"}, headers=h).json()
    assert sum(p["count"] for p in day["points"]) == 3


def test_timeseries_empty_range_gives_no_points(client, make_user, make_sensor, bearer):
    user = make_user("user")
    sensor = make_sensor(user)
    r = client.get(f"{BASE}/dashboard/timeseries", params={"sensor_id": sensor.id}, headers=bearer(user))
    assert r.status_code == 200 and r.json()["points"] == []


def test_timeseries_visibility(client, make_user, make_sensor, bearer):
    owner, other, admin, guest = make_user("user"), make_user("user"), make_user("admin"), make_user("guest")
    sensor = make_sensor(owner)
    url, params = f"{BASE}/dashboard/timeseries", {"sensor_id": sensor.id}
    assert client.get(url, params=params, headers=bearer(other)).status_code == 404
    assert client.get(url, params=params, headers=bearer(admin)).status_code == 200
    assert client.get(url, params=params, headers=bearer(guest)).status_code == 200
    assert client.get(url, params={"sensor_id": 9999}, headers=bearer(admin)).status_code == 404


def test_timeseries_validation(client, make_user, make_sensor, bearer):
    user = make_user("user")
    sensor = make_sensor(user)
    h = bearer(user)
    url = f"{BASE}/dashboard/timeseries"
    assert client.get(url, headers=h).status_code == 422                                              # sensor_id missing
    assert client.get(url, params={"sensor_id": sensor.id, "interval": "week"}, headers=h).status_code == 422
    assert client.get(url, params={"sensor_id": sensor.id, "from": iso(ago(hours=1)), "to": iso(ago(hours=3))}, headers=h).status_code == 422
    too_many = client.get(url, params={"sensor_id": sensor.id, "from": iso(ago(days=300)), "interval": "minute"}, headers=h)
    assert too_many.status_code == 422 and "Too many data points" in too_many.json()["detail"]
    assert client.get(url, params={"sensor_id": sensor.id}).status_code == 401
