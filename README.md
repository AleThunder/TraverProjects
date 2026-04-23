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

## Example Requests

Create a project with places:

```bash
curl -X POST http://127.0.0.1:8000/projects ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Chicago museum trip\",\"description\":\"Artworks to see\",\"start_date\":\"2026-05-01\",\"places\":[{\"external_id\":27992,\"notes\":\"Must see\"}]}"
```

Add a place to an existing project:

```bash
curl -X POST http://127.0.0.1:8000/projects/1/places ^
  -H "Content-Type: application/json" ^
  -d "{\"external_id\":28560,\"notes\":\"Check gallery info\"}"
```

Update notes and mark a place as visited:

```bash
curl -X PATCH http://127.0.0.1:8000/projects/1/places/1 ^
  -H "Content-Type: application/json" ^
  -d "{\"notes\":\"Visited on day one\",\"visited\":true}"
```

List projects:

```bash
curl "http://127.0.0.1:8000/projects?skip=0&limit=20"
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

## Business Rules

- A project can contain a maximum of 10 places.
- The same external artwork cannot be added twice to the same project.
- A project cannot be deleted if any of its places are marked as visited.
- A project is completed only when it has at least one place and all places are visited.
- Place validation uses `GET https://api.artic.edu/api/v1/artworks/{id}` with selected fields.
