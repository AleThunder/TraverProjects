from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    database_url: str = getenv("DATABASE_URL", "sqlite:///./travel_planner.db")
    artic_cache_ttl_seconds: int = int(getenv("ARTIC_CACHE_TTL_SECONDS", "300"))
    session_ttl_minutes: int = int(getenv("SESSION_TTL_MINUTES", "30"))


settings = Settings()
