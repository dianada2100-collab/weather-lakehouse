"""Data quality checks. Each check returns a CheckResult; failing runs stop before bad data
reaches the next layer (fail fast instead of silently publishing wrong numbers)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

log = logging.getLogger(__name__)


class DataQualityError(RuntimeError):
    """Raised when one or more quality checks fail."""


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def check_min_rows(df: pd.DataFrame, minimum: int) -> CheckResult:
    return CheckResult(f"min_rows>={minimum}", len(df) >= minimum, f"rows={len(df)}")


def check_not_null(df: pd.DataFrame, columns: list[str]) -> CheckResult:
    nulls = {c: int(df[c].isna().sum()) for c in columns if df[c].isna().any()}
    return CheckResult(f"not_null({','.join(columns)})", not nulls, f"null counts: {nulls}" if nulls else "")


def check_unique(df: pd.DataFrame, columns: list[str]) -> CheckResult:
    dupes = int(df.duplicated(subset=columns).sum())
    return CheckResult(f"unique({','.join(columns)})", dupes == 0, f"duplicate rows={dupes}")


def check_between(df: pd.DataFrame, column: str, low: float, high: float) -> CheckResult:
    """Non-null values must lie in [low, high]. Nulls are handled by check_null_ratio."""
    values = df[column].dropna()
    bad = int(((values < low) | (values > high)).sum())
    return CheckResult(f"between({column},{low},{high})", bad == 0, f"out of range={bad}")


def check_null_ratio(df: pd.DataFrame, column: str, max_ratio: float) -> CheckResult:
    ratio = float(df[column].isna().mean()) if len(df) else 1.0
    return CheckResult(f"null_ratio({column})<={max_ratio}", ratio <= max_ratio, f"ratio={ratio:.3f}")


def check_ordered(df: pd.DataFrame, low: str, mid: str, high: str) -> CheckResult:
    bad = int((~((df[low] <= df[mid]) & (df[mid] <= df[high]))).sum())
    return CheckResult(f"{low}<={mid}<={high}", bad == 0, f"violations={bad}")


def silver_checks(df: pd.DataFrame) -> list[CheckResult]:
    return [
        check_min_rows(df, 1),
        check_not_null(df, ["city", "ts"]),
        check_unique(df, ["city", "ts"]),
        check_between(df, "temperature_c", -60, 60),
        check_between(df, "precipitation_mm", 0, 500),   # per hour
        check_between(df, "wind_speed_kmh", 0, 400),
        check_null_ratio(df, "temperature_c", 0.05),
    ]


def gold_checks(fact: pd.DataFrame) -> list[CheckResult]:
    return [
        check_min_rows(fact, 1),
        check_not_null(fact, ["city_key", "date"]),
        check_unique(fact, ["city_key", "date"]),
        check_between(fact, "hours_observed", 1, 24),
        check_ordered(fact, "min_temp_c", "avg_temp_c", "max_temp_c"),
    ]


def assert_all_passed(results: list[CheckResult], dataset: str) -> None:
    failed = [r for r in results if not r.passed]
    for r in results:
        log.log(logging.ERROR if not r.passed else logging.INFO,
                "[dq:%s] %s -> %s %s", dataset, r.name, "OK" if r.passed else "FAIL", r.detail)
    if failed:
        names = ", ".join(r.name for r in failed)
        raise DataQualityError(f"{len(failed)} quality check(s) failed for {dataset}: {names}")
