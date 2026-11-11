from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    pwd_context,
    verify_password,
)
from app.models import RefreshToken, User, UserProfile, UserRole
from app.schemas.auth import TokenPair
from app.schemas.user import UserRegister
from app.services.activity import log_activity


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


# ---------- registration ----------
def register_user(db: Session, data: UserRegister, request: Request | None = None) -> User:
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        name=data.name,
        role=UserRole.user,  # self-registration never creates admins
        # With email verification on (Day 4) the account stays inactive until the link is used.
        is_active=not settings.REQUIRE_EMAIL_VERIFICATION,
        email_verified=False,
    )
    user.profile = UserProfile()
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two simultaneous sign-ups with the same email
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    db.refresh(user)
    log_activity(db, "auth.register", user_id=user.id, entity_type="user", entity_id=user.id, request=request)
    return user


# ---------- login ----------
def authenticate(db: Session, email: str, password: str, request: Request | None = None) -> User:
    email = email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        pwd_context.dummy_verify()  # keep timing similar whether or not the email exists
        log_activity(db, "auth.login_failed", details={"email": email}, request=request)
        raise _unauthorized("Incorrect email or password")
    if not verify_password(password, user.password_hash):
        log_activity(db, "auth.login_failed", user_id=user.id, details={"email": email}, request=request)
        raise _unauthorized("Incorrect email or password")

    # Only reveal account state after the password is proven correct.
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Email not verified")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    user.last_login = _now()
    db.commit()
    log_activity(db, "auth.login", user_id=user.id, entity_type="user", entity_id=user.id, request=request)
    return user


# ---------- tokens ----------
def issue_tokens(db: Session, user: User, lifetime: timedelta) -> TokenPair:
    raw_refresh = generate_refresh_token()
    now = _now()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=now + lifetime,
            created_at=now,
        )
    )
    db.commit()
    return TokenPair(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def login_tokens(db: Session, user: User, remember_me: bool) -> TokenPair:
    days = settings.REFRESH_TOKEN_REMEMBER_DAYS if remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
    return issue_tokens(db, user, timedelta(days=days))


def rotate_refresh_token(db: Session, raw_token: str, request: Request | None = None) -> TokenPair:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    if row is None:
        raise _unauthorized("Invalid refresh token")

    if row.revoked:
        # A revoked token being used again means it may have been stolen: close every session.
        db.execute(update(RefreshToken).where(RefreshToken.user_id == row.user_id).values(revoked=True))
        db.commit()
        log_activity(db, "auth.refresh_reuse", user_id=row.user_id, request=request)
        raise _unauthorized("Refresh token already used")

    if _aware(row.expires_at) <= _now():
        raise _unauthorized("Refresh token expired")

    user = row.user
    if not user.is_active:
        raise _unauthorized("Account is disabled")

    lifetime = _aware(row.expires_at) - _aware(row.created_at)  # keeps the "remember me" length
    row.revoked = True
    db.commit()
    return issue_tokens(db, user, lifetime)


def revoke_refresh_token(db: Session, raw_token: str, user: User, request: Request | None = None) -> None:
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(raw_token), RefreshToken.user_id == user.id
        )
    )
    if row is not None and not row.revoked:
        row.revoked = True
        db.commit()
    log_activity(db, "auth.logout", user_id=user.id, entity_type="user", entity_id=user.id, request=request)
