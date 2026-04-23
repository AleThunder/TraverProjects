# Travel Planner API

FastAPI CRUD application for managing travel projects and places. Places are validated against the public Art Institute of Chicago API before they are stored.

## Features

- Create, list, update, get, and delete travel projects.
- Create a project with up to 10 imported places in one request.
- Add Art Institute artworks as project places after validating the external ID.
- Update notes and mark project places as visited.
- Automatically mark a project as completed when all its places are visited.
- Prevent deleting a project when any place has already been visited.
- Prevent duplicate external places within the same project.
- Pagination for project listing endpoints.
- In-memory TTL caching for Art Institute API artwork lookups.
- User registration and 30-minute session authentication for project and place endpoints.
- Swagger/OpenAPI documentation at `/docs`.

## Setup

Python 3.11+ is recommended. The pinned dependencies also work with Python 3.14.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at:

- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

SQLite data is stored in `travel_planner.db`, created automatically on startup.

## Configuration

The app supports these environment variables:

```text
DATABASE_URL=sqlite:///./travel_planner.db
ARTIC_CACHE_TTL_SECONDS=300
SESSION_TTL_MINUTES=30
```

`/health`, `/user/register/`, and `/user/auth/` are public. Project and place endpoints require a valid session token. Passwords are hashed before they are stored.

## Docker

Build and run with Docker:

```bash
docker build -t travel-planner-api .
docker run --rm -p 8000:8000 -v travel_planner_data:/data -e DATABASE_URL=sqlite:////data/travel_planner.db travel-planner-api
```

Or use Docker Compose:

```bash
docker compose up --build
```

The container exposes the same URLs:

- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Docker Compose stores SQLite data in the named volume `travel_planner_data`.

## API Documentation

- Swagger/OpenAPI: `http://127.0.0.1:8000/docs`
- Postman collection: `Travel_Projects.postman_collection.json`
- Postman collection by url `https://beautymafiadev.postman.co/workspace/My-Workspace~c05af33c-e5df-45fe-8fed-93c86adffc58/collection/34553835-65d22337-386d-4c0a-a26f-b7141202c104?action=share&creator=34553835`

## Project Structure

```text
app/
  api/routes/      FastAPI route handlers and HTTP response metadata
  core/            Shared application exceptions
  repositories/    SQLAlchemy query helpers
  services/        Business rules and third-party API integration
  database.py      SQLite engine, session dependency, ORM base
  models.py        SQLAlchemy database models
  schemas.py       Pydantic request and response schemas
```

Routes stay thin and delegate validation/business decisions to services. Services raise application exceptions, and `app.main` maps those exceptions to consistent JSON HTTP responses.

## Example Requests

Register a user:

```bash
curl -X POST http://127.0.0.1:8000/user/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"traveller@example.com\",\"pass\":\"secret123\"}"
```

Create a 30-minute session:

```bash
curl -X POST http://127.0.0.1:8000/user/auth/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"traveller@example.com\",\"pass\":\"secret123\"}"
```

Use the returned `access_token` as a Bearer token for project and place endpoints.

Create a project with places:

```bash
curl -X POST http://127.0.0.1:8000/projects ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Chicago museum trip\",\"description\":\"Artworks to see\",\"start_date\":\"2026-05-01\",\"places\":[{\"external_id\":27992,\"notes\":\"Must see\"}]}"
```

Add a place to an existing project:

```bash
curl -X POST http://127.0.0.1:8000/projects/1/places ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"external_id\":28560,\"notes\":\"Check gallery info\"}"
```

Update notes and mark a place as visited:

```bash
curl -X PATCH http://127.0.0.1:8000/projects/1/places/1 ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"notes\":\"Visited on day one\",\"visited\":true}"
```

List projects:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "http://127.0.0.1:8000/projects?skip=0&limit=20"
```

## API Summary

### Projects

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `DELETE /projects/{project_id}`

### Places

- `POST /projects/{project_id}/places`
- `GET /projects/{project_id}/places`
- `GET /projects/{project_id}/places/{place_id}`
- `PATCH /projects/{project_id}/places/{place_id}`

### Users

- `POST /user/register/`
- `POST /user/auth/`

## Business Rules

- A project can contain a maximum of 10 places.
- The same external artwork cannot be added twice to the same project.
- A project cannot be deleted if any of its places are marked as visited.
- A project is completed only when it has at least one place and all places are visited.
- Place validation uses `GET https://api.artic.edu/api/v1/artworks/{id}` with selected fields.
