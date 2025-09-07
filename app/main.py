from datetime import date
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from .ipma_client import IPMAClient
from .schemas import LocalitiesResponse, DailyForecastResponse, DayForecastResponse

app = FastAPI(title="IPMA Weather Proxy API", version="1.0.0")
client = IPMAClient()


@app.get("/health")
async def health():
    """Liveness probe for the service.

    Returns
    -------
    dict
        A fixed payload `{"status": "ok"}` used by orchestrators and uptime checks.
    """

    return {"status": "ok"}


@app.get("/v1/localities", response_model=LocalitiesResponse)
async def list_localities(q: Optional[str] = Query(None, description="Case-insensitive filter by locality substring"),
                          district_id: Optional[int] = Query(None, description="IPMA district id (idDistrito)")):
    """List and optionally filter IPMA localities.

    Parameters
    ----------
    q : Optional[str]
        Case-insensitive substring to match against the `local` field.
    district_id : Optional[int]
        IPMA district id (`idDistrito`) to narrow down the result set.

    Returns
    -------
    LocalitiesResponse
        Envelope with `count` and `data` (list of locality records).

    Notes
    -----
    - The raw list is retrieved via `IPMAClient.get_localities()` and can be served
      from an in-memory TTL cache to reduce external requests.
    - Use this endpoint to discover the `globalIdLocal` that other endpoints consume.

    Examples
    --------
    - `GET /v1/localities?q=Lisboa`
    - `GET /v1/localities?district_id=11`
    """

    items = await client.get_localities()
    if q:
        qn = q.lower()
        items = [it for it in items if qn in it.get("local", "").lower()]
    if district_id is not None:
        items = [it for it in items if int(it.get("idDistrito", -1)) == int(district_id)]
    return {"count": len(items), "data": items}


@app.get("/v1/forecast/daily", response_model=DailyForecastResponse)
async def daily_forecast(
        global_id_local: Optional[int] = Query(None,
                                               description="IPMA globalIdLocal. If not provided, locality is required."),
        locality: Optional[str] = Query(None,
                                        description="Locality name, case-insensitive. Used when global_id_local is not provided."),
        district_id: Optional[int] = Query(None, description="Optional district id to disambiguate locality"),
):
    """Return the multi-day forecast for a given locality.

    Parameters
    ----------
    global_id_local : Optional[int]
        IPMA `globalIdLocal`. If omitted, `locality` must be provided.
    locality : Optional[str]
        Human-readable locality name (case-insensitive). Used to resolve `globalIdLocal`
        when it is not explicitly provided.
    district_id : Optional[int]
        Optional district id to disambiguate locality names that exist in multiple districts.

    Returns
    -------
    DailyForecastResponse
        Raw IPMA daily forecast payload (typically ~5 days).

    Raises
    ------
    HTTPException
        400 if neither `global_id_local` nor `locality` is provided.
        404 if the given `locality` cannot be resolved to a `globalIdLocal`.

    Notes
    -----
    - After fetching, numeric fields such as `tMin`, `tMax`, `precipitaProb`,
      `latitude`, `longitude` are normalized to `float` when possible for consistency.
    - Data may be served from a short-lived in-memory cache in `IPMAClient`.
    """

    if not global_id_local and not locality:
        raise HTTPException(status_code=400, detail="Provide either global_id_local or locality")
    if not global_id_local and locality:
        found = await client.find_locality(locality, district_id)
        if not found:
            raise HTTPException(status_code=404, detail="Locality not found")
        global_id_local = int(found["globalIdLocal"])
    data = await client.get_daily_forecast(int(global_id_local))
    # normalize numeric types
    for d in data.get("data", []):
        for k in ["tMin", "tMax", "precipitaProb", "latitude", "longitude"]:
            if k in d and d[k] is not None:
                try:
                    d[k] = float(d[k])
                except Exception:
                    pass
    return JSONResponse(content=data)


@app.get("/v1/forecast/day", response_model=DayForecastResponse)
async def forecast_for_day(
        forecast_date: date = Query(..., description="Target date in YYYY-MM-DD"),
        global_id_local: Optional[int] = Query(None),
        locality: Optional[str] = Query(None),
        district_id: Optional[int] = Query(None),
):
    """Return a normalized forecast for a single day.

    Parameters
    ----------
    forecast_date : date
        Target date in `YYYY-MM-DD` format. Must exist within the IPMA forecast window.
    global_id_local : Optional[int]
        IPMA `globalIdLocal`. If omitted, `locality` must be provided.
    locality : Optional[str]
        Locality name (case-insensitive) used to resolve `globalIdLocal` when not provided.
    district_id : Optional[int]
        Optional district id to disambiguate the locality.

    Returns
    -------
    DayForecastResponse
        Normalized single-day forecast including expanded weather and wind info.

    Raises
    ------
    HTTPException
        400 if neither `global_id_local` nor `locality` is provided.
        404 if the locality cannot be resolved or the date is outside the available window.

    Notes
    -----
    - Enriches `idWeatherType` using the weather-type mapping (PT/EN labels).
    - `wind` groups wind speed class and predominant direction into a compact object.
    - Values like `tMin`, `tMax`, `precipitaProb` are returned as floats.
    """

    if not global_id_local and not locality:
        raise HTTPException(status_code=400, detail="Provide either global_id_local or locality")
    if not global_id_local and locality:
        found = await client.find_locality(locality, district_id)
        if not found:
            raise HTTPException(status_code=404, detail="Locality not found")
        global_id_local = int(found["globalIdLocal"])

    data = await client.get_daily_forecast(int(global_id_local))
    day = next((d for d in data.get("data", []) if d.get("forecastDate") == forecast_date.isoformat()), None)
    if not day:
        raise HTTPException(status_code=404, detail="Date not in available forecast window")
    # enrich with weather type / wind class descriptions
    wtypes = await client.get_weather_types()
    wt = int(day.get("idWeatherType"))
    weather = {
        "id": wt,
        "pt": wtypes.get(wt, {}).get("pt", ""),
        "en": wtypes.get(wt, {}).get("en", ""),
    }
    wind = {
        "class": int(day.get("classWindSpeed")) if day.get("classWindSpeed") is not None else None,
        "dir": day.get("predWindDir"),
    }
    result = {
        "globalIdLocal": int(data.get("globalIdLocal")),
        "forecastDate": forecast_date.isoformat(),
        "tMin": float(day.get("tMin")),
        "tMax": float(day.get("tMax")),
        "precipitaProb": float(day.get("precipitaProb")),
        "predWindDir": day.get("predWindDir"),
        "weather": weather,
        "wind": wind,
    }
    return JSONResponse(content=result)
