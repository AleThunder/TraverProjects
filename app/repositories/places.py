from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models import ProjectPlace


def get_by_id_for_project(db: Session, project_id: int, place_id: int) -> ProjectPlace | None:
    """Fetch a single place that belongs to the given project."""
    return (
        db.query(ProjectPlace)
        .filter(ProjectPlace.project_id == project_id, ProjectPlace.id == place_id)
        .first()
    )


def list_for_project(db: Session, project_id: int) -> Sequence[ProjectPlace]:
    """Fetch all places for a project ordered by insertion ID."""
    return (
        db.query(ProjectPlace)
        .filter(ProjectPlace.project_id == project_id)
        .order_by(ProjectPlace.id)
        .all()
    )
