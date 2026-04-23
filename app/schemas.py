from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlaceImport(BaseModel):
    """Request schema for importing a place from the external artwork API."""

    external_id: int = Field(..., gt=0)
    notes: str | None = None


class ProjectBase(BaseModel):
    """Shared project fields used by create and read schemas."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    start_date: date | None = None


class ProjectCreate(ProjectBase):
    """Request schema for creating a project with optional initial places."""

    places: list[PlaceImport] | None = Field(default=None, max_length=10)

    @field_validator("places")
    @classmethod
    def validate_unique_places(cls, places: list[PlaceImport] | None) -> list[PlaceImport] | None:
        """Ensure provided initial places are non-empty and unique."""
        if places is None:
            return places
        if not places:
            raise ValueError("places must contain at least one item when provided")
        external_ids = [place.external_id for place in places]
        if len(external_ids) != len(set(external_ids)):
            raise ValueError("places must contain unique external_id values")
        return places


class ProjectUpdate(BaseModel):
    """Request schema for partially updating project metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    start_date: date | None = None


class PlaceCreate(PlaceImport):
    """Request schema for adding one place to an existing project."""

    pass


class PlaceUpdate(BaseModel):
    """Request schema for changing notes or visited state of a project place."""

    notes: str | None = None
    visited: bool | None = None


class PlaceRead(BaseModel):
    """Response schema for returning a project place."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    external_id: int
    title: str
    image_id: str | None
    artist_display: str | None
    date_display: str | None
    notes: str | None
    visited: bool
    created_at: datetime
    updated_at: datetime


class ProjectRead(BaseModel):
    """Response schema for returning project metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    start_date: date | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectRead):
    """Response schema for returning a project together with its places."""

    places: list[PlaceRead] = Field(default_factory=list)
