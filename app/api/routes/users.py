from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models import User
from app.schemas import AuthResponse, UserCredentials, UserRead
from app.services import users as user_service


router = APIRouter(prefix="/user", tags=["users"])


@router.post("/register/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCredentials, db: Session = Depends(get_db)) -> User:
    """Register a new user account with a securely hashed password."""
    return user_service.register_user(db, payload)


@router.post("/auth/", response_model=AuthResponse)
def authenticate_user(payload: UserCredentials, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate a user and create a session that expires in 30 minutes by default."""
    user, token, expires_at = user_service.authenticate_user(db, payload)
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        samesite="lax",
    )
    return AuthResponse(access_token=token, expires_at=expires_at, user=user)
