from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.database import get_db
from app.models import User
from app.services import users as user_service


bearer_scheme = HTTPBearer(auto_error=False)


def require_session_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from a Bearer token or session cookie."""
    token = credentials.credentials if credentials else request.cookies.get("session_token")
    if not token:
        raise UnauthorizedError("Authentication required")
    return user_service.get_user_by_session_token(db, token)
