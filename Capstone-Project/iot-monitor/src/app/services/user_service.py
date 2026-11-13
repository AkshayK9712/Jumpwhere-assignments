from fastapi import HTTPException, Request, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.sanitize import escape_like
from app.models import RefreshToken, User, UserProfile, UserRole
from app.schemas.common import PageParams, paginate
from app.schemas.user import AdminUserUpdate, UserProfileUpdate, UserUpdate
from app.services.activity import log_activity


def list_users(db: Session, params: PageParams, role: UserRole | None, is_active: bool | None, q: str | None) -> dict:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if q:
        pattern = f"%{escape_like(q.strip())}%"
        stmt = stmt.where(or_(User.name.ilike(pattern, escape="\\"), User.email.ilike(pattern, escape="\\")))
    return paginate(db, stmt.order_by(User.id), params)


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def update_me(db: Session, user: User, data: UserUpdate, request: Request | None = None) -> User:
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    log_activity(db, "user.update_self", user_id=user.id, entity_type="user", entity_id=user.id,
                 details={"fields": sorted(changes)}, request=request)
    return user


def admin_update_user(db: Session, actor: User, target: User, data: AdminUserUpdate, request: Request | None = None) -> User:
    changes = data.model_dump(exclude_unset=True)

    if target.id == actor.id:
        demoting = "role" in changes and changes["role"] != actor.role
        deactivating = changes.get("is_active") is False
        if demoting or deactivating:
            # prevents locking yourself (and possibly everyone) out of the admin panel
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role or deactivate your own account")

    for field, value in changes.items():
        setattr(target, field, value)

    if changes.get("is_active") is False:  # deactivated users lose all sessions immediately
        db.execute(update(RefreshToken).where(RefreshToken.user_id == target.id).values(revoked=True))

    db.commit()
    db.refresh(target)
    log_activity(
        db, "user.admin_update", user_id=actor.id, entity_type="user", entity_id=target.id,
        details={k: (v.value if isinstance(v, UserRole) else v) for k, v in changes.items()}, request=request,
    )
    return target


def delete_user(db: Session, actor: User, target: User, request: Request | None = None) -> None:
    if target.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete your own account")
    target_id, target_email = target.id, target.email
    db.delete(target)
    db.commit()
    log_activity(db, "user.delete", user_id=actor.id, entity_type="user", entity_id=target_id,
                 details={"email": target_email}, request=request)


def get_or_create_profile(db: Session, user: User) -> UserProfile:
    if user.profile is None:
        user.profile = UserProfile()
        db.commit()
        db.refresh(user)
    return user.profile


def replace_profile(db: Session, user: User, data: UserProfileUpdate, request: Request | None = None) -> UserProfile:
    profile = get_or_create_profile(db, user)
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    log_activity(db, "user.update_profile", user_id=user.id, entity_type="user", entity_id=user.id, request=request)
    return profile
