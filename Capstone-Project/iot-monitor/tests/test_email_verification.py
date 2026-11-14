import re

from app.core.security import create_access_token, create_email_token
from app.services import email

BASE = "/api/v1"
STRONG = "Str0ng!Pass"


def _register(client, address="bob@example.com"):
    return client.post(f"{BASE}/auth/register", json={"email": address, "password": STRONG, "name": "Bob"})


def _token_from_outbox(index=-1):
    match = re.search(r"token=([\w\-.]+)", email.OUTBOX[index]["body"])
    assert match, "no verification link in the email"
    return match.group(1)


def test_register_sends_verification_email(client):
    _register(client)
    assert len(email.OUTBOX) == 1
    assert email.OUTBOX[0]["to"] == "bob@example.com"
    assert "/ui/#/verify?token=" in email.OUTBOX[0]["body"]


def test_full_flow_register_verify_login(client):
    _register(client)
    token = _token_from_outbox()

    assert client.post(f"{BASE}/auth/login", data={"username": "bob@example.com", "password": STRONG}).status_code == 403

    r = client.get(f"{BASE}/auth/verify-email", params={"token": token})
    assert r.status_code == 200

    r = client.post(f"{BASE}/auth/login", data={"username": "bob@example.com", "password": STRONG})
    assert r.status_code == 200


def test_verify_twice_is_fine(client):
    _register(client)
    token = _token_from_outbox()
    assert client.get(f"{BASE}/auth/verify-email", params={"token": token}).status_code == 200
    assert client.get(f"{BASE}/auth/verify-email", params={"token": token}).status_code == 200


def test_verify_with_garbage_token_is_400(client):
    assert client.get(f"{BASE}/auth/verify-email", params={"token": "garbage"}).status_code == 400


def test_verify_with_expired_token_is_400(client):
    from datetime import timedelta

    user_id = _register(client).json()["id"]
    expired = create_email_token(user_id, "verify", expires_delta=timedelta(seconds=-1))
    assert client.get(f"{BASE}/auth/verify-email", params={"token": expired}).status_code == 400


def test_verify_with_access_token_is_400(client):
    user_id = _register(client).json()["id"]
    wrong_kind = create_access_token(user_id, "user")
    assert client.get(f"{BASE}/auth/verify-email", params={"token": wrong_kind}).status_code == 400


def test_verify_does_not_reactivate_a_disabled_user(client, make_user, db_session):
    user = make_user(verified=True, is_active=False)  # verified earlier, then disabled by an admin
    token = create_email_token(user.id, "verify")
    assert client.get(f"{BASE}/auth/verify-email", params={"token": token}).status_code == 200
    db_session.expire_all()
    db_session.refresh(user)
    assert user.is_active is False


def test_resend_for_unverified_user_sends_email(client):
    _register(client)
    email.OUTBOX.clear()
    r = client.post(f"{BASE}/auth/resend-verification", json={"email": "bob@example.com"})
    assert r.status_code == 200
    assert len(email.OUTBOX) == 1


def test_resend_gives_same_answer_for_unknown_and_verified_emails(client, make_user):
    make_user(email="done@example.com", verified=True)
    unknown = client.post(f"{BASE}/auth/resend-verification", json={"email": "ghost@example.com"})
    verified = client.post(f"{BASE}/auth/resend-verification", json={"email": "done@example.com"})
    assert unknown.status_code == verified.status_code == 200
    assert unknown.json() == verified.json()
    assert email.OUTBOX == []  # nothing was sent in either case
