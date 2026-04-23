from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, ExternalServiceError, NotFoundError
from app.models import ProjectPlace, TravelProject
from app.repositories import projects as project_repository
from app.schemas import ProjectCreate, ProjectUpdate
from app.services.artic import ArticAPIError, Artwork, ArtworkNotFoundError, fetch_artwork


MAX_PLACES_PER_PROJECT = 10


def get_project(db: Session, project_id: int) -> TravelProject:
    """Return a project or raise a domain-level not found error."""
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise NotFoundError("Project not found")
    return project


def list_projects(
    db: Session,
    *,
    skip: int,
    limit: int,
    completed: bool | None,
) -> Sequence[TravelProject]:
    """Return projects using the listing filters exposed by the API."""
    return project_repository.list_all(db, skip=skip, limit=limit, completed=completed)


async def create_project(db: Session, payload: ProjectCreate) -> TravelProject:
    """Create a project and optionally attach validated external artworks as places."""
    project = TravelProject(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
    )
    db.add(project)

    if payload.places:
        ensure_project_can_accept_places(project, len(payload.places))
        for place_payload in payload.places:
            artwork = await get_artwork(place_payload.external_id)
            project.places.append(build_place(project, artwork, place_payload.notes))

    refresh_project_completion(project)
    commit_or_conflict(db)
    db.refresh(project)
    return get_project(db, project.id)


def update_project(db: Session, project_id: int, payload: ProjectUpdate) -> TravelProject:
    """Update project metadata without changing its places."""
    project = get_project(db, project_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)

    commit_or_conflict(db)
    db.refresh(project)
    return get_project(db, project.id)


def delete_project(db: Session, project_id: int) -> None:
    """Delete a project unless one of its places is already visited."""
    project = get_project(db, project_id)
    if any(place.visited for place in project.places):
        raise BusinessRuleError("Project cannot be deleted because at least one place is marked as visited")

    db.delete(project)
    commit_or_conflict(db)


def refresh_project_completion(project: TravelProject) -> None:
    """Recalculate the completion flag from the project's places."""
    project.is_completed = bool(project.places) and all(place.visited for place in project.places)


def ensure_project_can_accept_places(project: TravelProject, places_to_add: int = 1) -> None:
    """Enforce the maximum number of places allowed in one project."""
    if len(project.places) + places_to_add > MAX_PLACES_PER_PROJECT:
        raise BusinessRuleError(f"A project can contain at most {MAX_PLACES_PER_PROJECT} places")


def ensure_place_is_unique(project: TravelProject, external_id: int) -> None:
    """Prevent adding the same external artwork to one project more than once."""
    if any(place.external_id == external_id for place in project.places):
        raise ConflictError("This external place is already added to the project")


async def get_artwork(external_id: int) -> Artwork:
    """Fetch an external artwork and translate integration failures into domain errors."""
    try:
        return await fetch_artwork(external_id)
    except ArtworkNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc
    except ArticAPIError as exc:
        raise ExternalServiceError(str(exc)) from exc


def build_place(project: TravelProject, artwork: Artwork, notes: str | None) -> ProjectPlace:
    """Create a ProjectPlace model from validated external artwork data."""
    return ProjectPlace(
        project=project,
        external_id=artwork.external_id,
        title=artwork.title,
        image_id=artwork.image_id,
        artist_display=artwork.artist_display,
        date_display=artwork.date_display,
        notes=notes,
    )


def commit_or_conflict(db: Session) -> None:
    """Commit a database transaction and expose constraint failures as conflicts."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A database constraint prevented this operation") from exc
