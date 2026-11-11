from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User
from app.schemas.user import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut, operation_id="get_me", summary="Get my account")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
