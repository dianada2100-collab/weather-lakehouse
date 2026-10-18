"""Orchestrator / CLI.

    python -m weather_pipeline.run --start 2025-01-01 --end 2025-01-07
    python -m weather_pipeline.run --steps silver,gold      # re-process without calling the API

Every step is idempotent: re-running it for the same window overwrites the same keys.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date, timedelta
from typing import Any

import pandas as pd

from . import quality
from .config import (
    CITIES, GOLD_DIM_KEY, GOLD_FACT_KEY, SILVER_PREFIX, load_settings,
)
from .extract import bronze_key, extract_all
from .storage import Storage, get_storage
from .transform import bronze_to_silver, build_dim_city, build_fact_daily, silver_partitions

log = logging.getLogger("weather_pipeline")
STEPS = ("extract", "silver", "gold")
_PARTITION_RE = re.compile(r"city=([^/]+)/date=([^/]+)/")


def silver_key(city: str, day: str) -> str:
    return f"{SILVER_PREFIX}city={city}/date={day}/part.parquet"


def run_silver(storage: Storage, cities: list[str], start: date, end: date) -> int:
    """bronze -> silver for the given window. Returns the number of partitions written."""
    written = 0
    for city in cities:
        wrapper = storage.read_json(bronze_key(city, start, end))
        silver = bronze_to_silver(wrapper)
        quality.assert_all_passed(quality.silver_checks(silver), f"silver/{city}")
        for _, day, part in silver_partitions(silver):
            storage.write_parquet(silver_key(city, day), part)
            written += 1
    log.info("silver: %d partitions written", written)
    return written


def read_silver(storage: Storage) -> pd.DataFrame:
    """Load every silver partition; city/date are recovered from the Hive-style path."""
    frames = []
    for key in storage.list_keys(SILVER_PREFIX):
        match = _PARTITION_RE.search(key)
        if not match:
            continue
        df = storage.read_parquet(key)
        df.insert(0, "city", match.group(1))
        df["date"] = match.group(2)
        frames.append(df)
    if not frames:
        raise RuntimeError("No silver data found - run the 'silver' step first")
    return pd.concat(frames, ignore_index=True)


def run_gold(storage: Storage) -> pd.DataFrame:
    """silver -> gold. Gold is small, so it is rebuilt completely from all silver partitions."""
    silver = read_silver(storage)
    dim_city = build_dim_city()
    fact = build_fact_daily(silver, dim_city)
    quality.assert_all_passed(quality.gold_checks(fact), "gold/fact_weather_daily")
    storage.write_parquet(GOLD_DIM_KEY, dim_city)
    storage.write_parquet(GOLD_FACT_KEY, fact)
    log.info("gold: %d fact rows, %d cities", len(fact), len(dim_city))
    return fact


def run_pipeline(
    storage: Storage,
    cities: list[str],
    start: date,
    end: date,
    steps: tuple[str, ...] = STEPS,
    session: Any | None = None,
) -> None:
    if start > end:
        raise ValueError(f"start {start} is after end {end}")
    if "extract" in steps:
        extract_all(storage, cities, start, end, session=session)
    if "silver" in steps:
        run_silver(storage, cities, start, end)
    if "gold" in steps:
        run_gold(storage)


def default_window(today: date | None = None) -> tuple[date, date]:
    """The archive API lags a few days behind, so default to the 7 days ending a week ago."""
    today = today or date.today()
    end = today - timedelta(days=7)
    return end - timedelta(days=6), end


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    d_start, d_end = default_window()
    p = argparse.ArgumentParser(description="Weather lakehouse pipeline")
    p.add_argument("--start", type=date.fromisoformat, default=d_start, help="YYYY-MM-DD")
    p.add_argument("--end", type=date.fromisoformat, default=d_end, help="YYYY-MM-DD")
    p.add_argument("--cities", default=",".join(CITIES), help="comma-separated, default: all")
    p.add_argument("--steps", default=",".join(STEPS), help="subset of: extract,silver,gold")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    steps = tuple(s.strip() for s in args.steps.split(",") if s.strip())
    unknown = [c for c in cities if c not in CITIES] + [s for s in steps if s not in STEPS]
    if unknown:
        log.error("unknown cities/steps: %s", unknown)
        return 1

    storage = get_storage(load_settings())
    log.info("run %s..%s cities=%s steps=%s", args.start, args.end, cities, steps)
    try:
        run_pipeline(storage, cities, args.start, args.end, steps)
    except quality.DataQualityError as exc:
        log.error("data quality failure: %s", exc)
        return 2
    except Exception:
        log.exception("pipeline failed")
        return 1
    log.info("pipeline finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
