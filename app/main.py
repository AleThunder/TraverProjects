from collections.abc import Sequence
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import Base, engine, get_db
from app.models import ProjectPlace, TravelProject
from app.schemas import (
    PlaceCreate,
    PlaceRead,
    PlaceUpdate,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ProjectUpdate,
)
from app.services.artic import ArticAPIError, Artwork, ArtworkNotFoundError, fetch_artwork


MAX_PLACES_PER_PROJECT = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Travel Planner API",
    description="CRUD API for travel projects and project places backed by the Art Institute of Chicago API.",
    version="0.1.0",
    lifespan=lifespan,
)


def get_project_or_404(db: Session, project_id: int) -> TravelProject:
    project = (
        db.query(TravelProject)
        .options(selectinload(TravelProject.places))
        .filter(TravelProject.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_project_place_or_404(db: Session, project_id: int, place_id: int) -> ProjectPlace:
    place = (
        db.query(ProjectPlace)
        .filter(ProjectPlace.project_id == project_id, ProjectPlace.id == place_id)
        .first()
    )
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found in this project")
    return place


def refresh_project_completion(project: TravelProject) -> None:
    project.is_completed = bool(project.places) and all(place.visited for place in project.places)


def ensure_project_can_accept_places(project: TravelProject, places_to_add: int = 1) -> None:
    if len(project.places) + places_to_add > MAX_PLACES_PER_PROJECT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A project can contain at most {MAX_PLACES_PER_PROJECT} places",
        )


def ensure_place_is_unique(project: TravelProject, external_id: int) -> None:
    if any(place.external_id == external_id for place in project.places):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This external place is already added to the project",
        )


async def get_artwork_or_http_error(external_id: int) -> Artwork:
    try:
        return await fetch_artwork(external_id)
    except ArtworkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ArticAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def build_place(project: TravelProject, artwork: Artwork, notes: str | None) -> ProjectPlace:
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
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A database constraint prevented this operation",
        ) from exc


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED, tags=["projects"])
async def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> TravelProject:
    project = TravelProject(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
    )
    db.add(project)

    if payload.places:
        ensure_project_can_accept_places(project, len(payload.places))
        for place_payload in payload.places:
            artwork = await get_artwork_or_http_error(place_payload.external_id)
            project.places.append(build_place(project, artwork, place_payload.notes))

    refresh_project_completion(project)
    commit_or_conflict(db)
    db.refresh(project)
    return get_project_or_404(db, project.id)


@app.get("/projects", response_model=list[ProjectRead], tags=["projects"])
def list_projects(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    completed: bool | None = None,
) -> Sequence[TravelProject]:
    query = db.query(TravelProject).order_by(TravelProject.id)
    if completed is not None:
        query = query.filter(TravelProject.is_completed == completed)
    return query.offset(skip).limit(limit).all()


@app.get("/projects/{project_id}", response_model=ProjectDetail, tags=["projects"])
def get_project(project_id: int, db: Session = Depends(get_db)) -> TravelProject:
    return get_project_or_404(db, project_id)


@app.patch("/projects/{project_id}", response_model=ProjectDetail, tags=["projects"])
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)) -> TravelProject:
    project = get_project_or_404(db, project_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)
    commit_or_conflict(db)
    db.refresh(project)
    return get_project_or_404(db, project.id)


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["projects"])
def delete_project(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = get_project_or_404(db, project_id)
    if any(place.visited for place in project.places):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project cannot be deleted because at least one place is marked as visited",
        )
    db.delete(project)
    commit_or_conflict(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/projects/{project_id}/places",
    response_model=PlaceRead,
    status_code=status.HTTP_201_CREATED,
    tags=["places"],
)
async def add_place(project_id: int, payload: PlaceCreate, db: Session = Depends(get_db)) -> ProjectPlace:
    project = get_project_or_404(db, project_id)
    ensure_project_can_accept_places(project)
    ensure_place_is_unique(project, payload.external_id)

    artwork = await get_artwork_or_http_error(payload.external_id)
    place = build_place(project, artwork, payload.notes)
    project.places.append(place)
    refresh_project_completion(project)
    commit_or_conflict(db)
    db.refresh(place)
    return place


@app.get("/projects/{project_id}/places", response_model=list[PlaceRead], tags=["places"])
def list_places(project_id: int, db: Session = Depends(get_db)) -> Sequence[ProjectPlace]:
    get_project_or_404(db, project_id)
    return (
        db.query(ProjectPlace)
        .filter(ProjectPlace.project_id == project_id)
        .order_by(ProjectPlace.id)
        .all()
    )


@app.get("/projects/{project_id}/places/{place_id}", response_model=PlaceRead, tags=["places"])
def get_place(project_id: int, place_id: int, db: Session = Depends(get_db)) -> ProjectPlace:
    get_project_or_404(db, project_id)
    return get_project_place_or_404(db, project_id, place_id)


@app.patch("/projects/{project_id}/places/{place_id}", response_model=PlaceRead, tags=["places"])
def update_place(
    project_id: int,
    place_id: int,
    payload: PlaceUpdate,
    db: Session = Depends(get_db),
) -> ProjectPlace:
    project = get_project_or_404(db, project_id)
    place = get_project_place_or_404(db, project_id, place_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(place, field, value)

    refresh_project_completion(project)
    commit_or_conflict(db)
    db.refresh(place)
    return place
