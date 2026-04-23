from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import health, places, projects
from app.core.exceptions import TravelPlannerError
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create database tables on startup for the lightweight SQLite MVP."""
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    fast_app = FastAPI(
        title="Travel Planner API",
        description="CRUD API for travel projects and project places backed by the Art Institute of Chicago API.",
        version="0.1.0",
        lifespan=lifespan,
    )

    fast_app.include_router(health.router)
    fast_app.include_router(projects.router)
    fast_app.include_router(places.router)

    @fast_app.exception_handler(TravelPlannerError)
    async def handle_travel_planner_error(request: Request, exc: TravelPlannerError) -> JSONResponse:
        """Convert expected domain errors into consistent JSON API responses."""
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return fast_app


app = create_app()
