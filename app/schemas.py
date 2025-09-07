from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date


class Locality(BaseModel):
    """Reference data for a locality (district capitals, islands, and a few extras).

    Notes
    -----
    - `latitude` and `longitude` are provided by IPMA as strings (decimal degrees).
    - `globalIdLocal` is the key used to query forecasts for this locality.
    """

    globalIdLocal: int
    local: str
    idRegiao: int
    idDistrito: int
    idConcelho: int
    idAreaAviso: str
    latitude: str
    longitude: str


class LocalitiesResponse(BaseModel):
    count: int
    data: List[Locality]


class WeatherType(BaseModel):
    idWeatherType: int
    descWeatherTypePT: str
    descWeatherTypeEN: str


class DailyForecastItem(BaseModel):
    forecastDate: date
    tMin: float
    tMax: float
    precipitaProb: float = Field(alias="precipitaProb")
    predWindDir: str
    idWeatherType: int
    classWindSpeed: int
    classPrecInt: int | None = None
    latitude: float | None = None
    longitude: float | None = None


class DailyForecastResponse(BaseModel):
    owner: str
    country: str
    globalIdLocal: int
    dataUpdate: str
    data: List[DailyForecastItem]


class DayForecastResponse(BaseModel):
    globalIdLocal: int
    forecastDate: date
    tMin: float
    tMax: float
    precipitaProb: float
    predWindDir: str
    weather: dict
    wind: dict
