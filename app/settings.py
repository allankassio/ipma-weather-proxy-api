from pydantic import BaseModel


class Settings(BaseModel):
    """Immutable runtime configuration for the API.

    Notes
    -----
    - Values here are not read from environment variables by default. If you
      want that behavior, migrate to `pydantic-settings` or load them before
      instantiating `Settings`.
    - TTLs (time-to-live) are expressed in seconds and control how long cached
      responses are considered fresh.
    """

    ipma_base_url: str = "https://api.ipma.pt/open-data"
    # TTLs (in seconds) for simple in-memory caching
    cache_ttl_localities: int = 12 * 60 * 60  # 12h, localities change rarely
    cache_ttl_classes: int = 12 * 60 * 60  # weather classes/labels
    cache_ttl_forecast: int = 30 * 60  # 30 minutes


settings = Settings()
