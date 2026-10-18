"""Extract: call the Open-Meteo archive API and land the raw response in the bronze layer."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any, Callable

import requests

from .config import API_URL, BRONZE_PREFIX, CITIES, HOURLY_VARS
from .storage import Storage

log = logging.getLogger(__name__)


class ExtractError(RuntimeError):
    """Raised when the API could not be reached after all retries."""


def bronze_key(city: str, start: date, end: date) -> str:
    # The key depends only on the requested window -> re-running overwrites, never duplicates.
    return f"{BRONZE_PREFIX}city={city}/start={start.isoformat()}_end={end.isoformat()}/raw.json"


def fetch_city(
    city: str,
    start: date,
    end: date,
    session: Any | None = None,
    max_attempts: int = 4,
    backoff_s: float = 2.0,
    timeout_s: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Fetch hourly data for one city. Retries network errors, HTTP 429 and 5xx with
    exponential backoff; other 4xx errors fail immediately (retrying will not help)."""
    lat, lon = CITIES[city]
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",
    }
    session = session or requests.Session()
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            resp = session.get(API_URL, params=params, timeout=timeout_s)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
        else:
            if resp.status_code == 429 or resp.status_code >= 500:
                last_error = RuntimeError(f"HTTP {resp.status_code}")
            else:
                resp.raise_for_status()  # 4xx -> raises, no retry
                return resp.json()

        if attempt < max_attempts:
            delay = backoff_s * 2 ** (attempt - 1)
            log.warning("fetch %s failed (attempt %d/%d): %s; retrying in %.1fs",
                        city, attempt, max_attempts, last_error, delay)
            sleep(delay)

    raise ExtractError(f"Could not fetch {city} after {max_attempts} attempts") from last_error


def extract_all(
    storage: Storage,
    cities: list[str],
    start: date,
    end: date,
    session: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[str]:
    """Fetch every city and write the raw payload (plus metadata) to bronze."""
    keys: list[str] = []
    for city in cities:
        payload = fetch_city(city, start, end, session=session, sleep=sleep)
        wrapper = {
            "meta": {
                "city": city,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "source": API_URL,
                "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            "payload": payload,
        }
        key = bronze_key(city, start, end)
        storage.write_json(key, wrapper)
        log.info("bronze written: %s", key)
        keys.append(key)
    return keys
