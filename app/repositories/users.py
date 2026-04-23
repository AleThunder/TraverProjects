from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from app.models import User, UserSession


def get_by_email(db: Session, email: str) -> User | None:
    """Fetch one user account by normalized email."""
    return db.query(User).filter(User.email == email).first()


def get_session_by_token_hash(db: Session, token_hash: str) -> UserSession | None:
    """Fetch an active-looking session with its user eagerly loaded."""
    return (
        db.query(UserSession)
        .options(selectinload(UserSession.user))
        .filter(UserSession.token_hash == token_hash)
        .first()
    )


def delete_expired_sessions(db: Session, now: datetime) -> None:
    """Remove sessions whose expiration time has passed."""
    db.query(UserSession).filter(UserSession.expires_at <= now).delete()
