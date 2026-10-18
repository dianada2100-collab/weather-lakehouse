"""Transform: bronze (raw JSON) -> silver (clean hourly table) -> gold (daily star schema)."""
from __future__ import annotations

from typing import Iterator

import pandas as pd

from .config import CITIES, HOURLY_VARS

SILVER_VALUE_COLUMNS = ["ts", "temperature_c", "precipitation_mm", "wind_speed_kmh"]
RAIN_THRESHOLD_MM = 1.0


def bronze_to_silver(wrapper: dict) -> pd.DataFrame:
    """Parse one raw API response into a typed, de-duplicated hourly table.

    Output columns: city, ts (naive UTC), temperature_c, precipitation_mm,
    wind_speed_kmh, date (YYYY-MM-DD string, used as partition key).
    """
    city = wrapper["meta"]["city"]
    hourly = (wrapper.get("payload") or {}).get("hourly")
    if not hourly or "time" not in hourly:
        raise ValueError(f"payload for {city!r} has no hourly.time")

    n = len(hourly["time"])
    columns: dict[str, list] = {"ts": hourly["time"]}
    for api_name, col_name in HOURLY_VARS.items():
        values = hourly.get(api_name, [None] * n)
        if len(values) != n:
            raise ValueError(f"{api_name!r} has {len(values)} values, expected {n}")
        columns[col_name] = values

    df = pd.DataFrame(columns)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce").dt.tz_localize(None)
    for col in HOURLY_VARS.values():
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    df = df.dropna(subset=["ts"])
    df.insert(0, "city", city)
    df = df.drop_duplicates(subset=["city", "ts"], keep="last").sort_values("ts")
    df["date"] = df["ts"].dt.strftime("%Y-%m-%d")
    return df.reset_index(drop=True)[["city", *SILVER_VALUE_COLUMNS, "date"]]


def silver_partitions(silver: pd.DataFrame) -> Iterator[tuple[str, str, pd.DataFrame]]:
    """Yield (city, date, rows) - one item per partition we write to the lake.
    The partition columns are dropped from the data: they live in the path (Hive style)."""
    for (city, day), part in silver.groupby(["city", "date"], sort=True):
        yield city, day, part[SILVER_VALUE_COLUMNS].reset_index(drop=True)


def build_dim_city(cities: dict[str, tuple[float, float]] = CITIES) -> pd.DataFrame:
    rows = [
        {"city_key": i, "city": name, "latitude": lat, "longitude": lon}
        for i, (name, (lat, lon)) in enumerate(cities.items(), start=1)
    ]
    return pd.DataFrame(rows)


def build_fact_daily(silver: pd.DataFrame, dim_city: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly silver rows to one row per city and day (grain: city x day)."""
    daily = silver.groupby(["city", "date"], as_index=False).agg(
        avg_temp_c=("temperature_c", "mean"),
        min_temp_c=("temperature_c", "min"),
        max_temp_c=("temperature_c", "max"),
        total_precip_mm=("precipitation_mm", "sum"),
        max_wind_kmh=("wind_speed_kmh", "max"),
        hours_observed=("temperature_c", "count"),
    )
    daily = daily.merge(dim_city[["city_key", "city"]], on="city", how="left", validate="many_to_one")
    daily["date"] = pd.to_datetime(daily["date"]).dt.date  # real DATE type in parquet/Athena
    daily["is_rainy_day"] = daily["total_precip_mm"] >= RAIN_THRESHOLD_MM
    for col in ["avg_temp_c", "min_temp_c", "max_temp_c", "total_precip_mm", "max_wind_kmh"]:
        daily[col] = daily[col].round(2)
    daily["hours_observed"] = daily["hours_observed"].astype("int64")

    columns = [
        "city_key", "date", "avg_temp_c", "min_temp_c", "max_temp_c",
        "total_precip_mm", "max_wind_kmh", "hours_observed", "is_rainy_day",
    ]
    return daily[columns].sort_values(["city_key", "date"]).reset_index(drop=True)
