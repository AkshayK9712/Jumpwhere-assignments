from sqlalchemy import select

from app.core.config import settings
from app.models import ActivityLog, RefreshToken

STRONG = "Str0ng!Pass"
BASE = "/api/v1"


def register(client, email="ann@example.com", password=STRONG, name="Ann"):
    return client.post(f"{BASE}/auth/register", json={"email": email, "password": password, "name": name})


def login(client, email="ann@example.com", password=STRONG, remember_me=False):
    return client.post(
        f"{BASE}/auth/login",
        data={"username": email, "password": password, "remember_me": str(remember_me).lower()},
    )


def auth_header(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------- registration ----------
def test_register_success(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "ann@example.com"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email_is_409(client):
    assert register(client).status_code == 201
    assert register(client, email="ANN@example.com").status_code == 409


def test_register_weak_password_is_422(client):
    assert register(client, password="password").status_code == 422


def test_register_invalid_email_is_422(client):
    assert register(client, email="not-an-email").status_code == 422


# ---------- login ----------
def test_login_returns_tokens(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert body["access_token"] and body["refresh_token"]


def test_login_wrong_password_is_401(client):
    register(client)
    assert login(client, password="Wrong!Pass1").status_code == 401


def test_login_unknown_user_is_401(client):
    assert login(client, email="nobody@example.com").status_code == 401


def test_login_requires_verified_email_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    assert register(client).status_code == 201
    r = login(client)
    assert r.status_code == 403
    assert "not verified" in r.json()["detail"].lower()


def test_remember_me_gives_longer_refresh_token(client, db_session):
    register(client)
    login(client, remember_me=False)
    login(client, remember_me=True)
    rows = db_session.scalars(select(RefreshToken).order_by(RefreshToken.id)).all()
    short, long_ = [(r.expires_at - r.created_at).days for r in rows]
    assert short == settings.REFRESH_TOKEN_EXPIRE_DAYS
    assert long_ == settings.REFRESH_TOKEN_REMEMBER_DAYS


# ---------- protected route ----------
def test_me_with_valid_token(client):
    register(client)
    tokens = login(client).json()
    r = client.get(f"{BASE}/users/me", headers=auth_header(tokens))
    assert r.status_code == 200
    assert r.json()["email"] == "ann@example.com"


def test_me_without_token_is_401(client):
    assert client.get(f"{BASE}/users/me").status_code == 401


def test_me_with_garbage_token_is_401(client):
    r = client.get(f"{BASE}/users/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


# ---------- refresh / logout ----------
def test_refresh_rotates_tokens(client):
    register(client)
    t1 = login(client).json()
    r = client.post(f"{BASE}/auth/refresh", json={"refresh_token": t1["refresh_token"]})
    assert r.status_code == 200
    t2 = r.json()
    assert t2["refresh_token"] != t1["refresh_token"]
    assert client.get(f"{BASE}/users/me", headers=auth_header(t2)).status_code == 200


def test_refresh_token_reuse_revokes_all_sessions(client):
    register(client)
    t1 = login(client).json()
    t2 = client.post(f"{BASE}/auth/refresh", json={"refresh_token": t1["refresh_token"]}).json()

    reuse = client.post(f"{BASE}/auth/refresh", json={"refresh_token": t1["refresh_token"]})
    assert reuse.status_code == 401
    # the legitimate newer token is revoked too
    after = client.post(f"{BASE}/auth/refresh", json={"refresh_token": t2["refresh_token"]})
    assert after.status_code == 401


def test_refresh_with_unknown_token_is_401(client):
    assert client.post(f"{BASE}/auth/refresh", json={"refresh_token": "nope"}).status_code == 401


def test_logout_revokes_refresh_token(client):
    register(client)
    t = login(client).json()
    r = client.post(f"{BASE}/auth/logout", json={"refresh_token": t["refresh_token"]}, headers=auth_header(t))
    assert r.status_code == 200
    assert client.post(f"{BASE}/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_logout_requires_auth(client):
    assert client.post(f"{BASE}/auth/logout", json={"refresh_token": "x"}).status_code == 401


# ---------- audit trail ----------
def test_auth_events_are_logged(client, db_session):
    register(client)
    login(client, password="Wrong!Pass1")
    login(client)
    actions = [a for a in db_session.scalars(select(ActivityLog.action))]
    assert {"auth.register", "auth.login_failed", "auth.login"} <= set(actions)
