from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class used by all SQLAlchemy ORM models."""

    pass


def get_db() -> Generator:
    """Yield a request-scoped SQLAlchemy session and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
