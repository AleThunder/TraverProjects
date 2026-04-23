from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import require_session_auth
from app.database import get_db
from app.models import ProjectPlace
from app.schemas import PlaceCreate, PlaceRead, PlaceUpdate
from app.services import places as place_service


router = APIRouter(prefix="/projects/{project_id}/places", tags=["places"], dependencies=[Depends(require_session_auth)])


@router.post("", response_model=PlaceRead, status_code=status.HTTP_201_CREATED)
async def add_place(project_id: int, payload: PlaceCreate, db: Session = Depends(get_db)) -> ProjectPlace:
    """Add one validated Art Institute artwork to an existing project."""
    return await place_service.add_place(db, project_id, payload)


@router.get("", response_model=list[PlaceRead])
def list_places(project_id: int, db: Session = Depends(get_db)) -> Sequence[ProjectPlace]:
    """List all places attached to a project."""
    return place_service.list_places(db, project_id)


@router.get("/{place_id}", response_model=PlaceRead)
def get_place(project_id: int, place_id: int, db: Session = Depends(get_db)) -> ProjectPlace:
    """Return one place from a project."""
    return place_service.get_place(db, project_id, place_id)


@router.patch("/{place_id}", response_model=PlaceRead)
def update_place(
    project_id: int,
    place_id: int,
    payload: PlaceUpdate,
    db: Session = Depends(get_db),
) -> ProjectPlace:
    """Update notes and/or visited status for a project place."""
    return place_service.update_place(db, project_id, place_id, payload)
