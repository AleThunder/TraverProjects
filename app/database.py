from collections.abc import Generator
from os import getenv

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = getenv("DATABASE_URL", "sqlite:///./travel_planner.db")

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
