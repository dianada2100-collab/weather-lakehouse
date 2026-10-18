import numpy as np
import pandas as pd
import pytest

from tests.helpers import make_wrapper
from weather_pipeline import quality
from weather_pipeline.transform import bronze_to_silver


def good_silver() -> pd.DataFrame:
    return bronze_to_silver(make_wrapper(days=2))


def test_good_data_passes_all_silver_checks():
    results = quality.silver_checks(good_silver())
    assert all(r.passed for r in results), [r for r in results if not r.passed]
    quality.assert_all_passed(results, "silver")        # must not raise


def test_unique_check_detects_duplicates():
    df = good_silver()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    assert not quality.check_unique(df, ["city", "ts"]).passed


def test_not_null_check_detects_nulls():
    df = good_silver()
    df.loc[0, "ts"] = pd.NaT
    result = quality.check_not_null(df, ["city", "ts"])
    assert not result.passed and "ts" in result.detail


@pytest.mark.parametrize("column, bad_value", [
    ("temperature_c", 99.0),
    ("precipitation_mm", -1.0),
    ("wind_speed_kmh", 1000.0),
])
def test_range_checks_detect_outliers(column, bad_value):
    df = good_silver()
    df.loc[5, column] = bad_value
    failed = [r for r in quality.silver_checks(df) if not r.passed]
    assert any(column in r.name for r in failed)


def test_null_ratio_check_threshold():
    df = good_silver()
    df.loc[:5, "temperature_c"] = np.nan                # 6 of 48 = 12.5 %
    assert not quality.check_null_ratio(df, "temperature_c", 0.05).passed
    assert quality.check_null_ratio(df, "temperature_c", 0.20).passed


def test_empty_frame_fails_min_rows():
    assert not quality.check_min_rows(good_silver().iloc[0:0], 1).passed


def test_assert_all_passed_raises_with_check_names():
    results = [quality.CheckResult("a", True), quality.CheckResult("b", False, "boom")]
    with pytest.raises(quality.DataQualityError, match="b"):
        quality.assert_all_passed(results, "demo")


def test_gold_ordering_check():
    fact = pd.DataFrame({"min_temp_c": [1.0, 5.0], "avg_temp_c": [2.0, 3.0], "max_temp_c": [3.0, 4.0]})
    assert not quality.check_ordered(fact, "min_temp_c", "avg_temp_c", "max_temp_c").passed
