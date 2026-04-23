from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlaceImport(BaseModel):
    external_id: int = Field(..., gt=0)
    notes: str | None = None


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    start_date: date | None = None


class ProjectCreate(ProjectBase):
    places: list[PlaceImport] | None = Field(default=None, max_length=10)

    @field_validator("places")
    @classmethod
    def validate_unique_places(cls, places: list[PlaceImport] | None) -> list[PlaceImport] | None:
        if places is None:
            return places
        if not places:
            raise ValueError("places must contain at least one item when provided")
        external_ids = [place.external_id for place in places]
        if len(external_ids) != len(set(external_ids)):
            raise ValueError("places must contain unique external_id values")
        return places


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    start_date: date | None = None


class PlaceCreate(PlaceImport):
    pass


class PlaceUpdate(BaseModel):
    notes: str | None = None
    visited: bool | None = None


class PlaceRead(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    start_date: date | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectRead):
    places: list[PlaceRead] = Field(default_factory=list)
