from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin, require_writer
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.common import PageParams
from app.schemas.user import (
    AdminUserUpdate, UserOut, UserPage, UserProfileOut, UserProfileUpdate, UserUpdate,
)
from app.services import user_service

router = APIRouter()


# ----- my account (declared before /{user_id} so "me" is never read as an id) -----
@router.get("/me", response_model=UserOut, operation_id="get_me", summary="Get my account")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut, operation_id="update_me", summary="Update my account")
def update_me(payload: UserUpdate, request: Request, current_user: User = Depends(require_writer),
              db: Session = Depends(get_db)):
    return user_service.update_me(db, current_user, payload, request)


@router.get("/me/profile", response_model=UserProfileOut, operation_id="get_my_profile", summary="Get my profile")
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.get_or_create_profile(db, current_user)


@router.put("/me/profile", response_model=UserProfileOut, operation_id="put_my_profile",
            summary="Create or replace my profile")
def put_my_profile(payload: UserProfileUpdate, request: Request, current_user: User = Depends(require_writer),
                   db: Session = Depends(get_db)):
    return user_service.replace_profile(db, current_user, payload, request)


# ----- admin: user management -----
@router.get("", response_model=UserPage, operation_id="list_users", summary="List users")
def list_users(
    params: PageParams = Depends(),
    role: UserRole | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None, max_length=100, description="Search name or email"),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_service.list_users(db, params, role, is_active, q)


@router.get("/{user_id}", response_model=UserOut, operation_id="get_user", summary="Get a user")
def get_user(user_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return user_service.get_user_or_404(db, user_id)


@router.patch("/{user_id}", response_model=UserOut, operation_id="admin_update_user",
              summary="Update role / active state")
def admin_update_user(user_id: int, payload: AdminUserUpdate, request: Request,
                      admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = user_service.get_user_or_404(db, user_id)
    return user_service.admin_update_user(db, admin, target, payload, request)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_user",
               summary="Delete a user", response_class=Response)
def delete_user(user_id: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = user_service.get_user_or_404(db, user_id)
    user_service.delete_user(db, admin, target, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
