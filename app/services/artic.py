from dataclasses import dataclass

import httpx


ARTIC_BASE_URL = "https://api.artic.edu/api/v1"
ARTIC_FIELDS = "id,title,image_id,artist_display,date_display"


class ArticAPIError(Exception):
    pass


class ArtworkNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class Artwork:
    external_id: int
    title: str
    image_id: str | None
    artist_display: str | None
    date_display: str | None


async def fetch_artwork(external_id: int) -> Artwork:
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

    return Artwork(
        external_id=int(data["id"]),
        title=data.get("title") or f"Artwork {external_id}",
        image_id=data.get("image_id"),
        artist_display=data.get("artist_display"),
        date_display=data.get("date_display"),
    )
