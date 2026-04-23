import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services import projects as project_service
from app.services.artic import Artwork, cache_artwork, clear_artwork_cache, get_cached_artwork


USER_EMAIL = "traveller@example.com"
USER_PASSWORD = "secret123"


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
    clear_artwork_cache()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    clear_artwork_cache()
    Base.metadata.drop_all(bind=engine)


def auth_headers(client) -> dict[str, str]:
    """Register and authenticate a user, returning Bearer auth headers."""
    client.post("/user/register/", json={"email": USER_EMAIL, "pass": USER_PASSWORD})
    response = client.post("/user/auth/", json={"email": USER_EMAIL, "pass": USER_PASSWORD})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_and_authenticate_user(client):
    register_response = client.post("/user/register/", json={"email": USER_EMAIL, "pass": USER_PASSWORD})
    auth_response = client.post("/user/auth/", json={"email": USER_EMAIL, "pass": USER_PASSWORD})

    assert register_response.status_code == 201
    assert register_response.json()["email"] == USER_EMAIL
    assert "password_hash" not in register_response.json()
    assert auth_response.status_code == 200
    assert auth_response.json()["token_type"] == "bearer"
    assert auth_response.cookies.get("session_token")


def test_user_routes_work_without_redirects(client):
    register_response = client.post(
        "/user/register",
        json={"email": "no-redirect@example.com", "pass": USER_PASSWORD},
        follow_redirects=False,
    )
    auth_response = client.post(
        "/user/auth",
        json={"email": "no-redirect@example.com", "pass": USER_PASSWORD},
        follow_redirects=False,
    )

    assert register_response.status_code == 201
    assert auth_response.status_code == 200


def test_reject_duplicate_user_registration(client):
    client.post("/user/register/", json={"email": USER_EMAIL, "pass": USER_PASSWORD})
    response = client.post("/user/register/", json={"email": USER_EMAIL, "pass": USER_PASSWORD})

    assert response.status_code == 409


def test_create_project_with_place_and_complete_it(client):
    headers = auth_headers(client)
    response = client.post(
        "/projects",
        headers=headers,
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
        headers=headers,
        json={"visited": True},
    )

    assert visit_response.status_code == 200
    assert visit_response.json()["visited"] is True
    assert client.get(f"/projects/{project_id}", headers=headers).json()["is_completed"] is True


def test_prevent_duplicate_place(client):
    headers = auth_headers(client)
    project = client.post("/projects", headers=headers, json={"name": "Trip"}).json()

    first = client.post(f"/projects/{project['id']}/places", headers=headers, json={"external_id": 27992})
    duplicate = client.post(f"/projects/{project['id']}/places", headers=headers, json={"external_id": 27992})

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_project_place_limit(client):
    headers = auth_headers(client)
    places = [{"external_id": external_id} for external_id in range(1, 11)]
    project = client.post("/projects", headers=headers, json={"name": "Full trip", "places": places}).json()

    response = client.post(f"/projects/{project['id']}/places", headers=headers, json={"external_id": 11})

    assert response.status_code == 400


def test_reject_empty_places_array_when_provided(client):
    headers = auth_headers(client)
    response = client.post("/projects", headers=headers, json={"name": "Trip", "places": []})

    assert response.status_code == 422


def test_prevent_deleting_project_with_visited_place(client):
    headers = auth_headers(client)
    project = client.post(
        "/projects",
        headers=headers,
        json={"name": "Trip", "places": [{"external_id": 27992}]},
    ).json()
    place_id = project["places"][0]["id"]

    client.patch(f"/projects/{project['id']}/places/{place_id}", headers=headers, json={"visited": True})
    response = client.delete(f"/projects/{project['id']}", headers=headers)

    assert response.status_code == 400


def test_crud_routes_require_session_auth(client):
    response = client.get("/projects")

    assert response.status_code == 401


def test_place_listing_returns_all_project_places(client):
    headers = auth_headers(client)
    places = [{"external_id": external_id} for external_id in range(1, 4)]
    project = client.post("/projects", headers=headers, json={"name": "Trip", "places": places}).json()

    response = client.get(f"/projects/{project['id']}/places", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert [place["external_id"] for place in body] == [1, 2, 3]


def test_artwork_cache_stores_successful_lookups():
    artwork = Artwork(
        external_id=42,
        title="Cached artwork",
        image_id=None,
        artist_display=None,
        date_display=None,
    )

    cache_artwork(artwork)

    assert get_cached_artwork(42) == artwork
