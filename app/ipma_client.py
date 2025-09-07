from typing import Any, Dict, List, Optional

import httpx

from .cache import TTLCache
from .settings import settings

_localities_cache = TTLCache(settings.cache_ttl_localities)
_weather_types_cache = TTLCache(settings.cache_ttl_classes)
_forecast_cache = TTLCache(settings.cache_ttl_forecast)


class IPMAClient:
    """Thin async client for IPMA open-data.

    Parameters
    ----------
    base_url : Optional[str]
        Base URL for IPMA endpoints. Defaults to `settings.ipma_base_url`.

    Notes
    -----
    - Uses `httpx` with a 20s timeout per request.
    - Relies on simple TTL caches defined at module level.
    - Intended for read-only workloads.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.ipma_base_url

    async def _get_json(self, url: str) -> Any:
        """Perform a GET request and return the parsed JSON payload.

        Parameters
        ----------
        url : str
            Fully qualified URL to fetch.

        Returns
        -------
        Any
            Parsed JSON as Python types.

        Raises
        ------
        httpx.HTTPStatusError
            If the response has a 4xx/5xx status code.
        httpx.RequestError
            For transport-level errors (DNS, timeouts, etc.).
        """

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()

    async def get_localities(self) -> List[Dict[str, Any]]:
        """Fetch the list of reference localities.

        Returns
        -------
        List[Dict[str, Any]]
            Raw locality items as provided by IPMA (subset of fields).

        Notes
        -----
        - Served from `_localities_cache` when available.
        - Source: `{base_url}/distrits-islands.json`.
        """

        key = "localities"
        cached = _localities_cache.get(key)
        if cached is not None:
            return cached
        url = f"{self.base_url}/distrits-islands.json"
        data = await self._get_json(url)
        items = data.get("data", [])
        _localities_cache.set(key, items)
        return items

    async def get_weather_types(self) -> Dict[int, Dict[str, str]]:
        """Fetch and map weather types to localized labels.

        Returns
        -------
        Dict[int, Dict[str, str]]
            Mapping: `idWeatherType` → `{"pt": <pt>, "en": <en>}`.

        Notes
        -----
        - Served from `_weather_types_cache` when available.
        - Source: `{base_url}/weather-type-classe.json`.
        """

        key = "weather_types"
        cached = _weather_types_cache.get(key)
        if cached is not None:
            return cached
        url = f"{self.base_url}/weather-type-classe.json"
        data = await self._get_json(url)
        mapping = {}
        for it in data.get("data", []):
            mapping[int(it["idWeatherType"])] = {
                "pt": it.get("descWeatherTypePT", ""),
                "en": it.get("descWeatherTypeEN", ""),
            }
        _weather_types_cache.set(key, mapping)
        return mapping

    async def get_daily_forecast(self, global_id_local: int) -> Dict[str, Any]:
        """Fetch the multi-day forecast for a locality.

        Parameters
        ----------
        global_id_local : int
            IPMA locality identifier (`globalIdLocal`).

        Returns
        -------
        Dict[str, Any]
            Raw forecast payload as returned by IPMA.

        Notes
        -----
        - Served from `_forecast_cache` when available.
        - Source: `{base_url}/forecast/meteorology/cities/daily/{global_id_local}.json`.
        """

        cache_key = f"forecast:{global_id_local}"
        cached = _forecast_cache.get(cache_key)
        if cached is not None:
            return cached
        url = f"{self.base_url}/forecast/meteorology/cities/daily/{global_id_local}.json"
        data = await self._get_json(url)
        _forecast_cache.set(cache_key, data)
        return data

    async def find_locality(self, locality: str, district_id: int | None = None) -> Optional[Dict[str, Any]]:
        """Resolve a human-readable locality name to a locality record.

        The search prefers an exact, case-insensitive match. If `district_id` is
        provided, it filters candidates to that district. If no exact match is found,
        a substring ("contains") search is attempted.

        Parameters
        ----------
        locality : str
            Locality name to match (case-insensitive).
        district_id : Optional[int]
            Optional `idDistrito` to disambiguate duplicate names across districts.

        Returns
        -------
        Optional[Dict[str, Any]]
            The selected locality dict (e.g., containing `globalIdLocal`) or `None` if not found.
        """

        locs = await self.get_localities()
        locality_norm = locality.strip().lower()
        # Prefer exact match within district if provided
        candidates = [l for l in locs if l.get("local", "").lower() == locality_norm]
        if district_id is not None:
            candidates = [l for l in candidates if int(l.get("idDistrito", -1)) == int(district_id)]
        if candidates:
            # If multiple, choose the one with the lowest idConcelho (stable)
            return \
            sorted(candidates, key=lambda x: (x.get("idConcelho", 1_000_000), x.get("globalIdLocal", 1_000_000)))[0]
        # fallback: contains
        contains = [l for l in locs if locality_norm in l.get("local", "").lower()]
        if district_id is not None:
            contains = [l for l in contains if int(l.get("idDistrito", -1)) == int(district_id)]
        if contains:
            return sorted(contains, key=lambda x: (x.get("idConcelho", 1_000_000), x.get("globalIdLocal", 1_000_000)))[
                0]
        return None
