from fastapi import APIRouter, Depends, Form, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.auth import Message, RefreshRequest, TokenPair
from app.schemas.user import UserOut, UserRegister
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, operation_id="register",
             summary="Register a new account")
def register(payload: UserRegister, request: Request, db: Session = Depends(get_db)):
    return auth_service.register_user(db, payload, request)


@router.post("/login", response_model=TokenPair, operation_id="login", summary="Log in and get tokens")
def login(
    request: Request,
    username: str = Form(..., description="The account email"),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db),
):
    user = auth_service.authenticate(db, username, password, request)
    return auth_service.login_tokens(db, user, remember_me)


@router.post("/refresh", response_model=TokenPair, operation_id="refresh_token",
             summary="Exchange a refresh token for a new token pair")
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    return auth_service.rotate_refresh_token(db, payload.refresh_token, request)


@router.post("/logout", response_model=Message, operation_id="logout", summary="Log out (revoke refresh token)")
def logout(
    payload: RefreshRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.revoke_refresh_token(db, payload.refresh_token, current_user, request)
    return Message(message="Logged out")
