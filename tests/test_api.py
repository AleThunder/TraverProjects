import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services import projects as project_service
from app.services.artic import Artwork


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    async def fake_artwork(external_id: int):
        return Artwork(
            external_id=external_id,
            title=f"Artwork {external_id}",
            image_id="image-id",
            artist_display="Artist",
            date_display="1884",
        )

    monkeypatch.setattr(project_service, "get_artwork", fake_artwork)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_create_project_with_place_and_complete_it(client):
    response = client.post(
        "/projects",
        json={
            "name": "Chicago trip",
            "places": [{"external_id": 27992, "notes": "Must see"}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_completed"] is False
    assert body["places"][0]["title"] == "Artwork 27992"

    project_id = body["id"]
    place_id = body["places"][0]["id"]
    visit_response = client.patch(
        f"/projects/{project_id}/places/{place_id}",
        json={"visited": True},
    )

    assert visit_response.status_code == 200
    assert visit_response.json()["visited"] is True
    assert client.get(f"/projects/{project_id}").json()["is_completed"] is True


def test_prevent_duplicate_place(client):
    project = client.post("/projects", json={"name": "Trip"}).json()

    first = client.post(f"/projects/{project['id']}/places", json={"external_id": 27992})
    duplicate = client.post(f"/projects/{project['id']}/places", json={"external_id": 27992})

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_project_place_limit(client):
    places = [{"external_id": external_id} for external_id in range(1, 11)]
    project = client.post("/projects", json={"name": "Full trip", "places": places}).json()

    response = client.post(f"/projects/{project['id']}/places", json={"external_id": 11})

    assert response.status_code == 400


def test_reject_empty_places_array_when_provided(client):
    response = client.post("/projects", json={"name": "Trip", "places": []})

    assert response.status_code == 422


def test_prevent_deleting_project_with_visited_place(client):
    project = client.post(
        "/projects",
        json={"name": "Trip", "places": [{"external_id": 27992}]},
    ).json()
    place_id = project["places"][0]["id"]

    client.patch(f"/projects/{project['id']}/places/{place_id}", json={"visited": True})
    response = client.delete(f"/projects/{project['id']}")

    assert response.status_code == 400
