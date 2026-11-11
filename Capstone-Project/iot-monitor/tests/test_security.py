from datetime import timedelta

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token, decode_access_token, generate_refresh_token,
    hash_password, hash_token, password_problems, verify_password,
)


def test_password_hash_and_verify():
    hashed = hash_password("Str0ng!Pass")
    assert hashed != "Str0ng!Pass"
    assert verify_password("Str0ng!Pass", hashed)
    assert not verify_password("wrong", hashed)


def test_hashes_are_salted():
    assert hash_password("Str0ng!Pass") != hash_password("Str0ng!Pass")


def test_password_strength_rules():
    assert password_problems("Str0ng!Pass") == []
    assert len(password_problems("password")) >= 3
    assert "a symbol" in password_problems("Password1")
    assert "at least 8 characters" in password_problems("Ab1!")


def test_access_token_roundtrip():
    token = create_access_token(5, "admin")
    claims = decode_access_token(token)
    assert claims["sub"] == "5"
    assert claims["role"] == "admin"
    assert claims["type"] == "access"


def test_expired_token_is_rejected():
    token = create_access_token(5, "user", expires_delta=timedelta(seconds=-1))
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token(5, "user")
    bad = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(JWTError):
        decode_access_token(bad)


def test_refresh_token_helpers():
    t = generate_refresh_token()
    assert len(t) > 40
    assert hash_token(t) == hash_token(t)
    assert len(hash_token(t)) == 64
    assert generate_refresh_token() != t
