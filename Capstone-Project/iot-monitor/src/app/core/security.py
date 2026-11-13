"""Password hashing, password rules and JWT helpers."""
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- passwords ----------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def password_problems(password: str) -> list[str]:
    """Return a list of unmet password rules (empty list = strong enough)."""
    problems = []
    if len(password) < 8:
        problems.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"\d", password):
        problems.append("a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a symbol")
    return problems


# ---------- access tokens (JWT) ----------
def create_access_token(user_id: int, role: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta is not None else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    claims = {"sub": str(user_id), "role": role, "type": "access", "iat": now, "exp": expire}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jose.JWTError if the token is invalid, expired or not an access token."""
    claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if claims.get("type") != "access":
        raise JWTError("Not an access token")
    return claims


# ---------- refresh tokens (opaque, stored hashed) ----------
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- email tokens (verification links) ----------
def create_email_token(user_id: int, purpose: str, expires_delta: timedelta | None = None) -> str:
    """Signed, expiring token for links sent by email. `purpose` e.g. "verify"."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta is not None else timedelta(hours=settings.VERIFY_TOKEN_EXPIRE_HOURS))
    claims = {"sub": str(user_id), "type": purpose, "iat": now, "exp": expire}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_email_token(token: str, purpose: str) -> dict:
    """Raises JWTError if invalid, expired, or issued for a different purpose."""
    claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if claims.get("type") != purpose:
        raise JWTError("Wrong token purpose")
    return claims
