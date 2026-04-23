from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.passwords import hash_password, hash_session_token, verify_password
from app.models import User, UserSession
from app.repositories import users as user_repository
from app.schemas import UserCredentials


def register_user(db: Session, payload: UserCredentials) -> User:
    """Create a user with a hashed password after validating email uniqueness."""
    if user_repository.get_by_email(db, payload.email):
        raise ConflictError("User with this email already exists")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("User with this email already exists") from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserCredentials) -> tuple[User, str, datetime]:
    """Validate user credentials and create a 30-minute session token."""
    user = user_repository.get_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    now = utc_now()
    user_repository.delete_expired_sessions(db, now)

    token = token_urlsafe(32)
    expires_at = now + timedelta(minutes=settings.session_ttl_minutes)
    db.add(UserSession(user=user, token_hash=hash_session_token(token), expires_at=expires_at))
    db.commit()
    return user, token, expires_at


def get_user_by_session_token(db: Session, token: str) -> User:
    """Return the user for a valid non-expired session token."""
    session = user_repository.get_session_by_token_hash(db, hash_session_token(token))
    if not session or session.expires_at <= utc_now():
        raise UnauthorizedError("Invalid or expired session")
    return session.user


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
