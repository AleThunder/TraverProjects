from dataclasses import dataclass
from time import monotonic

import httpx

from app.core.config import settings


ARTIC_BASE_URL = "https://api.artic.edu/api/v1"
ARTIC_FIELDS = "id,title,image_id,artist_display,date_display"
_artwork_cache: dict[int, tuple[float, "Artwork"]] = {}


class ArticAPIError(Exception):
    """Raised when the Art Institute API cannot complete a request."""

    pass


class ArtworkNotFoundError(Exception):
    """Raised when the Art Institute API has no artwork for the requested ID."""

    pass


@dataclass(frozen=True)
class Artwork:
    """Normalized artwork data used by the rest of the application."""

    external_id: int
    title: str
    image_id: str | None
    artist_display: str | None
    date_display: str | None


async def fetch_artwork(external_id: int) -> Artwork:
    """Fetch and normalize one artwork from the Art Institute of Chicago API with TTL caching."""
    cached_artwork = get_cached_artwork(external_id)
    if cached_artwork:
        return cached_artwork

    url = f"{ARTIC_BASE_URL}/artworks/{external_id}"
    params = {"fields": ARTIC_FIELDS}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise ArticAPIError("Could not reach Art Institute of Chicago API") from exc

    if response.status_code == 404:
        raise ArtworkNotFoundError(f"Artwork {external_id} was not found")

    if response.status_code >= 400:
        raise ArticAPIError("Art Institute of Chicago API returned an error")

    payload = response.json()
    data = payload.get("data")
    if not data or data.get("id") is None:
        raise ArtworkNotFoundError(f"Artwork {external_id} was not found")

    artwork = Artwork(
        external_id=int(data["id"]),
        title=data.get("title") or f"Artwork {external_id}",
        image_id=data.get("image_id"),
        artist_display=data.get("artist_display"),
        date_display=data.get("date_display"),
    )
    cache_artwork(artwork)
    return artwork


def get_cached_artwork(external_id: int) -> Artwork | None:
    """Return a cached artwork when it exists and has not expired."""
    cached = _artwork_cache.get(external_id)
    if not cached:
        return None

    expires_at, artwork = cached
    if expires_at <= monotonic():
        _artwork_cache.pop(external_id, None)
        return None
    return artwork


def cache_artwork(artwork: Artwork) -> None:
    """Store successful external artwork lookups for the configured TTL."""
    if settings.artic_cache_ttl_seconds <= 0:
        return
    _artwork_cache[artwork.external_id] = (monotonic() + settings.artic_cache_ttl_seconds, artwork)


def clear_artwork_cache() -> None:
    """Clear the in-memory artwork cache, primarily for tests and local debugging."""
    _artwork_cache.clear()
