"""Shared test helpers: synthetic API responses, a fake HTTP session and an in-memory storage."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from weather_pipeline.storage import Storage


def make_payload(start: date, days: int, base_temp: float = 10.0) -> dict:
    """Build an Open-Meteo-like response with `days` * 24 hourly values."""
    times, temps, precip, wind = [], [], [], []
    t0 = datetime(start.year, start.month, start.day)
    for h in range(days * 24):
        times.append((t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"))
        temps.append(base_temp + (h % 24) * 0.5)      # 10.0 .. 21.5 each day
        precip.append(0.5 if h % 24 < 4 else 0.0)      # 2.0 mm per day
        wind.append(5.0 + (h % 24))                    # 5 .. 28 km/h
    return {"hourly": {"time": times, "temperature_2m": temps,
                       "precipitation": precip, "wind_speed_10m": wind}}


def make_wrapper(city: str = "munich", start: date = date(2025, 1, 1), days: int = 2,
                 base_temp: float = 10.0) -> dict:
    end = start + timedelta(days=days - 1)
    return {
        "meta": {"city": city, "start": start.isoformat(), "end": end.isoformat()},
        "payload": make_payload(start, days, base_temp),
    }


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


class FakeSession:
    """Returns the queued responses in order; records every call."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class CitySession:
    """Answers every request with a valid payload for the requested window."""

    def __init__(self, days: int = 2):
        self.days = days
        self.calls = 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        start = date.fromisoformat(params["start_date"])
        return FakeResponse(200, make_payload(start, self.days))


class MemoryStorage(Storage):
    """Dict-backed storage; keeps DataFrames as objects so tests need no parquet engine."""

    def __init__(self):
        self.objects: dict[str, object] = {}

    def write_bytes(self, key, data):
        self.objects[key] = data

    def read_bytes(self, key):
        return self.objects[key]

    def list_keys(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))

    def write_json(self, key, obj):  # round-trip through JSON like the real backends
        self.objects[key] = json.dumps(obj).encode("utf-8")

    def write_parquet(self, key, df: pd.DataFrame):
        self.objects[key] = df.copy()

    def read_parquet(self, key) -> pd.DataFrame:
        return self.objects[key].copy()
