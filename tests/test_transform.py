from datetime import date

import pandas as pd
import pytest

from tests.helpers import make_wrapper
from weather_pipeline.transform import (
    bronze_to_silver, build_dim_city, build_fact_daily, silver_partitions,
)


def test_bronze_to_silver_shape_and_types():
    df = bronze_to_silver(make_wrapper(days=2))
    assert list(df.columns) == ["city", "ts", "temperature_c", "precipitation_mm", "wind_speed_kmh", "date"]
    assert len(df) == 48
    assert df["ts"].dt.tz is None                      # naive UTC
    assert str(df["temperature_c"].dtype) == "float64"
    assert df["date"].nunique() == 2
    assert df["ts"].is_monotonic_increasing


def test_duplicate_timestamps_are_removed():
    wrapper = make_wrapper(days=1)
    hourly = wrapper["payload"]["hourly"]
    for key in hourly:                                 # duplicate the first hour
        hourly[key].append(hourly[key][0])
    df = bronze_to_silver(wrapper)
    assert len(df) == 24
    assert not df.duplicated(["city", "ts"]).any()


def test_invalid_timestamps_are_dropped():
    wrapper = make_wrapper(days=1)
    wrapper["payload"]["hourly"]["time"][3] = "not-a-timestamp"
    assert len(bronze_to_silver(wrapper)) == 23


def test_non_numeric_values_become_nan():
    wrapper = make_wrapper(days=1)
    wrapper["payload"]["hourly"]["temperature_2m"][0] = "n/a"
    wrapper["payload"]["hourly"]["precipitation"][1] = None
    df = bronze_to_silver(wrapper)
    assert df["temperature_c"].isna().sum() == 1
    assert df["precipitation_mm"].isna().sum() == 1


@pytest.mark.parametrize("broken", [{}, {"hourly": {}}, {"hourly": {"temperature_2m": [1]}}])
def test_missing_hourly_time_raises(broken):
    wrapper = {"meta": {"city": "munich"}, "payload": broken}
    with pytest.raises(ValueError):
        bronze_to_silver(wrapper)


def test_length_mismatch_raises():
    wrapper = make_wrapper(days=1)
    wrapper["payload"]["hourly"]["precipitation"].pop()
    with pytest.raises(ValueError):
        bronze_to_silver(wrapper)


def test_silver_is_idempotent():
    a = bronze_to_silver(make_wrapper())
    b = bronze_to_silver(make_wrapper())
    pd.testing.assert_frame_equal(a, b)


def test_partitions_drop_partition_columns():
    parts = list(silver_partitions(bronze_to_silver(make_wrapper(days=2))))
    assert [(c, d) for c, d, _ in parts] == [("munich", "2025-01-01"), ("munich", "2025-01-02")]
    assert all(len(p) == 24 and "city" not in p.columns and "date" not in p.columns for _, _, p in parts)


def test_dim_city_has_unique_keys():
    dim = build_dim_city()
    assert dim["city_key"].is_unique and dim["city"].is_unique
    assert dim["city_key"].min() == 1


def test_fact_daily_aggregates_are_correct():
    silver = bronze_to_silver(make_wrapper(days=2, base_temp=10.0))
    fact = build_fact_daily(silver, build_dim_city())
    assert len(fact) == 2
    first = fact.iloc[0]
    assert first["date"] == date(2025, 1, 1)
    assert first["min_temp_c"] == 10.0
    assert first["max_temp_c"] == 21.5
    assert first["avg_temp_c"] == 15.75                # mean of 10.0 .. 21.5 step 0.5
    assert first["total_precip_mm"] == 2.0
    assert first["max_wind_kmh"] == 28.0
    assert first["hours_observed"] == 24
    assert bool(first["is_rainy_day"]) is True


def test_fact_daily_grain_is_city_x_day():
    frames = [bronze_to_silver(make_wrapper(city=c, days=3)) for c in ("munich", "berlin")]
    fact = build_fact_daily(pd.concat(frames, ignore_index=True), build_dim_city())
    assert len(fact) == 6
    assert not fact.duplicated(["city_key", "date"]).any()
    assert fact["city_key"].notna().all()
