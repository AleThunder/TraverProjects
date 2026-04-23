from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import require_session_auth
from app.database import get_db
from app.models import TravelProject
from app.schemas import ProjectCreate, ProjectDetail, ProjectRead, ProjectUpdate
from app.services import projects as project_service


router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(require_session_auth)])


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> TravelProject:
    """Create a travel project, optionally importing validated places in the same request."""
    return await project_service.create_project(db, payload)


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    completed: bool | None = None,
) -> Sequence[TravelProject]:
    """List travel projects with optional pagination and completion filtering."""
    return project_service.list_projects(db, skip=skip, limit=limit, completed=completed)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)) -> TravelProject:
    """Return one travel project with its places."""
    return project_service.get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)) -> TravelProject:
    """Update editable travel project fields."""
    return project_service.update_project(db, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a project when none of its places are marked as visited."""
    project_service.delete_project(db, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
