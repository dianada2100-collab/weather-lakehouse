from datetime import date

import pytest
import requests

from tests.helpers import FakeResponse, FakeSession, MemoryStorage, make_payload
from weather_pipeline.extract import ExtractError, bronze_key, extract_all, fetch_city

START, END = date(2025, 1, 1), date(2025, 1, 2)


def test_success_on_first_attempt():
    session = FakeSession([FakeResponse(200, make_payload(START, 2))])
    data = fetch_city("munich", START, END, session=session, sleep=lambda s: None)
    assert "hourly" in data
    params = session.calls[0]["params"]
    assert params["start_date"] == "2025-01-01" and params["end_date"] == "2025-01-02"
    assert params["timezone"] == "UTC"


def test_retries_on_5xx_then_succeeds_with_exponential_backoff():
    sleeps: list[float] = []
    session = FakeSession([FakeResponse(503), FakeResponse(500), FakeResponse(200, make_payload(START, 1))])
    fetch_city("berlin", START, END, session=session, sleep=sleeps.append, backoff_s=1.0)
    assert len(session.calls) == 3
    assert sleeps == [1.0, 2.0]


def test_retries_on_connection_error_and_429():
    session = FakeSession([requests.ConnectionError("boom"), FakeResponse(429),
                           FakeResponse(200, make_payload(START, 1))])
    assert "hourly" in fetch_city("munich", START, END, session=session, sleep=lambda s: None)


def test_gives_up_after_max_attempts():
    session = FakeSession([FakeResponse(500)] * 3)
    with pytest.raises(ExtractError):
        fetch_city("munich", START, END, session=session, max_attempts=3, sleep=lambda s: None)
    assert len(session.calls) == 3


def test_client_error_is_not_retried():
    session = FakeSession([FakeResponse(400), FakeResponse(200, make_payload(START, 1))])
    with pytest.raises(requests.HTTPError):
        fetch_city("munich", START, END, session=session, sleep=lambda s: None)
    assert len(session.calls) == 1


def test_extract_all_writes_one_bronze_object_per_city_and_is_idempotent():
    storage = MemoryStorage()
    session = FakeSession([FakeResponse(200, make_payload(START, 2)) for _ in range(4)])
    keys = extract_all(storage, ["munich", "berlin"], START, END, session=session)
    assert keys == [bronze_key("munich", START, END), bronze_key("berlin", START, END)]
    wrapper = storage.read_json(keys[0])
    assert wrapper["meta"]["city"] == "munich" and "ingested_at" in wrapper["meta"]

    extract_all(storage, ["munich", "berlin"], START, END, session=session)  # run again
    assert len(storage.list_keys("bronze/")) == 2                            # still 2 objects
