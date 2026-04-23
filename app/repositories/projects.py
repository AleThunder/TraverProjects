from collections.abc import Sequence

from sqlalchemy.orm import Session, selectinload

from app.models import TravelProject


def get_by_id(db: Session, project_id: int) -> TravelProject | None:
    """Fetch a project with its places eagerly loaded."""
    return (
        db.query(TravelProject)
        .options(selectinload(TravelProject.places))
        .filter(TravelProject.id == project_id)
        .first()
    )


def list_all(
    db: Session,
    *,
    skip: int,
    limit: int,
    completed: bool | None,
) -> Sequence[TravelProject]:
    """Fetch projects with pagination and optional completion filtering."""
    query = db.query(TravelProject).order_by(TravelProject.id)
    if completed is not None:
        query = query.filter(TravelProject.is_completed == completed)
    return query.offset(skip).limit(limit).all()
