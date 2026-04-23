from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight application health status."""
    return {"status": "ok"}
