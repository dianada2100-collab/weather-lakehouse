"""Central configuration. Everything environment-specific comes from env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass

# city -> (latitude, longitude). Order defines the surrogate key in dim_city.
CITIES: dict[str, tuple[float, float]] = {
    "munich": (48.1351, 11.5820),
    "berlin": (52.5200, 13.4050),
    "hamburg": (53.5511, 9.9937),
    "frankfurt": (50.1109, 8.6821),
    "cologne": (50.9375, 6.9603),
}

# Open-Meteo hourly variable -> column name in the silver layer
HOURLY_VARS: dict[str, str] = {
    "temperature_2m": "temperature_c",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}

API_URL = "https://archive-api.open-meteo.com/v1/archive"

BRONZE_PREFIX = "bronze/weather/"
SILVER_PREFIX = "silver/hourly_weather/"
GOLD_FACT_KEY = "gold/fact_weather_daily/data.parquet"
GOLD_DIM_KEY = "gold/dim_city/data.parquet"


@dataclass(frozen=True)
class Settings:
    backend: str  # "local" or "s3"
    local_root: str
    s3_bucket: str
    s3_prefix: str


def load_settings() -> Settings:
    return Settings(
        backend=os.getenv("STORAGE_BACKEND", "local").lower(),
        local_root=os.getenv("LOCAL_ROOT", "data"),
        s3_bucket=os.getenv("S3_BUCKET", ""),
        s3_prefix=os.getenv("S3_PREFIX", "weather-pipeline"),
    )
