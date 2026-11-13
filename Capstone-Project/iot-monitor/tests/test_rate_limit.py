from app.core.config import settings

BASE = "/api/v1"


def test_login_is_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 3)

    codes = []
    for _ in range(5):
        r = client.post(f"{BASE}/auth/login", data={"username": "x@example.com", "password": "nope"})
        codes.append(r.status_code)
    assert codes == [401, 401, 401, 429, 429]
    assert int(r.headers["Retry-After"]) >= 1


def test_logged_in_users_are_limited_individually(client, make_user, bearer, monkeypatch):
    a, b = make_user("user"), make_user("user")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 2)

    codes = [client.get(f"{BASE}/users/me", headers=bearer(a)).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert client.get(f"{BASE}/users/me", headers=bearer(b)).status_code == 200  # b has their own allowance


def test_rate_limit_headers(client, make_user, bearer, monkeypatch):
    user = make_user("user")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 10)
    r = client.get(f"{BASE}/users/me", headers=bearer(user))
    assert r.headers["X-RateLimit-Limit"] == "10"
    assert r.headers["X-RateLimit-Remaining"] == "9"


def test_health_is_never_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 1)
    assert [client.get(f"{BASE}/health").status_code for _ in range(4)] == [200] * 4
    assert [client.get("/health").status_code for _ in range(4)] == [200] * 4


def test_every_response_has_request_id_and_version(client):
    r = client.get(f"{BASE}/health")
    assert r.headers["X-API-Version"] == "1"
    assert r.headers["X-Request-ID"]
    r = client.get(f"{BASE}/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"
