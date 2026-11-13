BASE = "/api/v1"


def test_activity_logs_are_admin_only(client, make_user, bearer):
    assert client.get(f"{BASE}/admin/activity-logs", headers=bearer(make_user("user"))).status_code == 403
    assert client.get(f"{BASE}/admin/activity-logs", headers=bearer(make_user("guest"))).status_code == 403
    assert client.get(f"{BASE}/admin/activity-logs").status_code == 401


def test_activity_logs_filtering(client, make_user, bearer):
    admin, user = make_user("admin"), make_user("user")
    client.post(f"{BASE}/sensors", json={"title": "S", "category": "flow"}, headers=bearer(user))

    h = bearer(admin)
    everything = client.get(f"{BASE}/admin/activity-logs", headers=h).json()
    assert everything["total"] >= 1

    created = client.get(f"{BASE}/admin/activity-logs", params={"action": "sensor.create"}, headers=h).json()
    assert created["total"] == 1
    entry = created["items"][0]
    assert entry["user_id"] == user.id and entry["entity_type"] == "sensor"

    by_user = client.get(f"{BASE}/admin/activity-logs", params={"user_id": user.id}, headers=h).json()
    assert by_user["total"] == 1
    assert client.get(f"{BASE}/admin/activity-logs", params={"entity_type": "nothing"}, headers=h).json()["total"] == 0


def test_config_create_update_read(client, make_user, bearer):
    admin = make_user("admin")
    h = bearer(admin)
    url = f"{BASE}/admin/config/feature.dark_mode"

    assert client.get(url, headers=h).status_code == 404

    r = client.put(url, json={"value": {"enabled": True}, "description": "Dark theme"}, headers=h)
    assert r.status_code == 200
    first_id = r.json()["id"]
    assert r.json()["updated_by"] == admin.id

    r = client.put(url, json={"value": False}, headers=h)
    assert r.status_code == 200 and r.json()["id"] == first_id and r.json()["value"] is False

    assert client.get(url, headers=h).json()["value"] is False
    assert [c["key"] for c in client.get(f"{BASE}/admin/config", headers=h).json()] == ["feature.dark_mode"]


def test_config_is_admin_only(client, make_user, bearer):
    user = make_user("user")
    assert client.get(f"{BASE}/admin/config", headers=bearer(user)).status_code == 403
    assert client.put(f"{BASE}/admin/config/x", json={"value": 1}, headers=bearer(user)).status_code == 403


def test_config_key_format(client, make_user, bearer):
    h = bearer(make_user("admin"))
    assert client.put(f"{BASE}/admin/config/BAD_KEY", json={"value": 1}, headers=h).status_code == 422
    assert client.put(f"{BASE}/admin/config/ok_key-1.2", json={"value": 1}, headers=h).status_code == 200
