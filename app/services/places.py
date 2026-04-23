from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import ProjectPlace
from app.repositories import places as place_repository
from app.schemas import PlaceCreate, PlaceUpdate
from app.services import projects as project_service


async def add_place(db: Session, project_id: int, payload: PlaceCreate) -> ProjectPlace:
    """Add a validated Art Institute artwork to an existing project."""
    project = project_service.get_project(db, project_id)
    project_service.ensure_project_can_accept_places(project)
    project_service.ensure_place_is_unique(project, payload.external_id)

    artwork = await project_service.get_artwork(payload.external_id)
    place = project_service.build_place(project, artwork, payload.notes)
    project.places.append(place)
    project_service.refresh_project_completion(project)
    project_service.commit_or_conflict(db)
    db.refresh(place)
    return place


def list_places(db: Session, project_id: int) -> Sequence[ProjectPlace]:
    """Return all places for a project after confirming the project exists."""
    project_service.get_project(db, project_id)
    return place_repository.list_for_project(db, project_id)


def get_place(db: Session, project_id: int, place_id: int) -> ProjectPlace:
    """Return a project place or raise a not found error."""
    project_service.get_project(db, project_id)
    return get_project_place(db, project_id, place_id)


def get_project_place(db: Session, project_id: int, place_id: int) -> ProjectPlace:
    """Return a place by project and place IDs without refetching the project."""
    place = place_repository.get_by_id_for_project(db, project_id, place_id)
    if not place:
        raise NotFoundError("Place not found in this project")
    return place


def update_place(db: Session, project_id: int, place_id: int, payload: PlaceUpdate) -> ProjectPlace:
    """Update place notes or visited status and refresh project completion."""
    project = project_service.get_project(db, project_id)
    place = get_project_place(db, project_id, place_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(place, field, value)

    project_service.refresh_project_completion(project)
    project_service.commit_or_conflict(db)
    db.refresh(place)
    return place
