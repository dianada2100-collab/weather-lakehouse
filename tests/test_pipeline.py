from datetime import date

import pandas as pd
import pytest

from tests.helpers import CitySession, MemoryStorage
from weather_pipeline import run
from weather_pipeline.config import GOLD_DIM_KEY, GOLD_FACT_KEY, SILVER_PREFIX
from weather_pipeline.quality import DataQualityError

START, END = date(2025, 1, 1), date(2025, 1, 3)
CITIES = ["munich", "berlin", "hamburg"]


def run_all(storage, session=None, **kw):
    run.run_pipeline(storage, CITIES, START, END, session=session or CitySession(days=3), **kw)


def test_end_to_end_creates_all_layers():
    storage = MemoryStorage()
    run_all(storage)
    assert len(storage.list_keys("bronze/")) == 3
    assert len(storage.list_keys(SILVER_PREFIX)) == 3 * 3          # city x day partitions
    fact = storage.read_parquet(GOLD_FACT_KEY)
    assert len(fact) == 9 and fact["hours_observed"].eq(24).all()
    assert len(storage.read_parquet(GOLD_DIM_KEY)) == 5            # dim has all configured cities


def test_pipeline_is_idempotent():
    storage = MemoryStorage()
    run_all(storage)
    keys_1 = sorted(storage.objects)
    fact_1 = storage.read_parquet(GOLD_FACT_KEY)
    run_all(storage)
    assert sorted(storage.objects) == keys_1                       # no new/duplicate objects
    pd.testing.assert_frame_equal(fact_1, storage.read_parquet(GOLD_FACT_KEY))


def test_steps_can_run_without_api_calls():
    storage = MemoryStorage()
    run_all(storage)
    session = CitySession()
    run.run_pipeline(storage, CITIES, START, END, steps=("silver", "gold"), session=session)
    assert session.calls == 0


def test_gold_accumulates_across_windows():
    storage = MemoryStorage()
    run_all(storage)
    run.run_pipeline(storage, ["munich"], date(2025, 1, 10), date(2025, 1, 11),
                     session=CitySession(days=2))
    fact = storage.read_parquet(GOLD_FACT_KEY)
    assert len(fact) == 9 + 2


def test_bad_data_stops_pipeline_before_silver_is_written():
    storage = MemoryStorage()
    run.run_pipeline(storage, ["munich"], START, END, steps=("extract",), session=CitySession(days=3))
    key = storage.list_keys("bronze/")[0]
    wrapper = storage.read_json(key)
    wrapper["payload"]["hourly"]["temperature_2m"][0] = 999.0       # impossible temperature
    storage.write_json(key, wrapper)
    with pytest.raises(DataQualityError):
        run.run_silver(storage, ["munich"], START, END)
    assert storage.list_keys(SILVER_PREFIX) == []


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        run.run_pipeline(MemoryStorage(), CITIES, END, START)


def test_default_window_is_seven_days_ending_a_week_ago():
    start, end = run.default_window(today=date(2025, 3, 15))
    assert (start, end) == (date(2025, 3, 2), date(2025, 3, 8))


def test_main_rejects_unknown_city():
    assert run.main(["--cities", "atlantis"]) == 1
