import pandas as pd
import pytest

from python_practice.solutions import (
    chunked, count_by_level, dedupe_latest, flatten_json, incremental_filter, mask_email,
    null_report, parse_log_line, pseudonymize, retry, top_error_services, top_n_per_group,
    upsert, validate_record,
)


# 1
def test_dedupe_latest_keeps_newest_and_first_seen_order():
    rows = [
        {"id": 2, "ts": 1, "v": "old"}, {"id": 1, "ts": 5, "v": "a"},
        {"id": 2, "ts": 3, "v": "new"}, {"id": 1, "ts": 2, "v": "stale"},
    ]
    assert dedupe_latest(rows, "id", "ts") == [{"id": 2, "ts": 3, "v": "new"}, {"id": 1, "ts": 5, "v": "a"}]


def test_dedupe_latest_tie_goes_to_later_input():
    rows = [{"id": 1, "ts": 1, "v": "first"}, {"id": 1, "ts": 1, "v": "second"}]
    assert dedupe_latest(rows, "id", "ts")[0]["v"] == "second"


# 2
def test_flatten_json_nested_dicts_and_lists():
    data = {"a": {"b": 1, "c": {"d": 2}}, "e": [10, {"f": 3}], "g": None}
    assert flatten_json(data) == {"a.b": 1, "a.c.d": 2, "e.0": 10, "e.1.f": 3, "g": None}


def test_flatten_json_custom_separator_and_empty_containers():
    assert flatten_json({"a": {"b": 1}, "c": [], "d": {}}, sep="_") == {"a_b": 1, "c": [], "d": {}}


# 3
def test_chunked_splits_with_remainder():
    assert list(chunked(range(7), 3)) == [[0, 1, 2], [3, 4, 5], [6]]


def test_chunked_is_lazy_and_validates_size():
    assert next(chunked(iter(range(10**9)), 2)) == [0, 1]          # would hang if it were eager
    with pytest.raises(ValueError):
        list(chunked([1], 0))


# 4
def test_retry_succeeds_after_transient_failures():
    calls, sleeps = [], []

    @retry(max_attempts=3, backoff_s=1.0, sleep=sleeps.append)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("temporary")
        return "ok"

    assert flaky() == "ok" and len(calls) == 3 and sleeps == [1.0, 2.0]


def test_retry_reraises_after_last_attempt_and_ignores_other_exceptions():
    @retry(max_attempts=2, exceptions=(ConnectionError,), sleep=lambda s: None)
    def always_fails():
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        always_fails()

    @retry(max_attempts=5, exceptions=(ConnectionError,), sleep=lambda s: None)
    def wrong_error():
        raise KeyError("not retried")

    with pytest.raises(KeyError):
        wrong_error()


# 5
LOGS = [
    "2025-01-01 12:00:00 INFO api: started",
    "2025-01-01 12:00:01 ERROR payment-service: timeout while calling bank",
    "2025-01-01 12:00:02 ERROR payment-service: timeout again",
    "2025-01-01 12:00:03 ERROR auth: invalid token",
    "garbage line",
    "2025-01-01 12:00:05 WARN api: slow response",
]


def test_parse_log_line():
    assert parse_log_line(LOGS[1]) == {
        "ts": "2025-01-01 12:00:01", "level": "ERROR",
        "service": "payment-service", "message": "timeout while calling bank"}
    assert parse_log_line("garbage line") is None


def test_count_by_level_and_top_error_services():
    assert count_by_level(LOGS) == {"INFO": 1, "ERROR": 3, "WARN": 1}
    assert top_error_services(LOGS, n=1) == [("payment-service", 2)]
    assert top_error_services(LOGS) == [("payment-service", 2), ("auth", 1)]


# 6
SCHEMA = {"id": {"type": int, "required": True}, "email": {"type": str, "required": True},
          "age": {"type": int}}


def test_validate_record_ok():
    assert validate_record({"id": 1, "email": "a@b.de", "age": 30}, SCHEMA) == []
    assert validate_record({"id": 1, "email": "a@b.de"}, SCHEMA) == []          # optional field


def test_validate_record_reports_all_problems():
    errors = validate_record({"id": "1", "age": True, "foo": 1}, SCHEMA)
    assert errors == [
        "age: expected int, got bool", "email: missing required field",
        "foo: unexpected field", "id: expected int, got str"]


# 7
def test_incremental_filter_returns_new_rows_and_advances_watermark():
    rows = [{"id": 1, "ts": 10}, {"id": 2, "ts": 20}, {"id": 3, "ts": 30}]
    new, mark = incremental_filter(rows, 10, "ts")
    assert [r["id"] for r in new] == [2, 3] and mark == 30


def test_incremental_filter_keeps_watermark_when_nothing_new():
    assert incremental_filter([{"ts": 5}], 10, "ts") == ([], 10)


# 8
def test_upsert_inserts_updates_and_is_idempotent():
    existing = {1: {"id": 1, "name": "Anna", "city": "Munich"}}
    incoming = [{"id": 1, "city": "Berlin"}, {"id": 2, "name": "Ben", "city": "Hamburg"}]
    once = upsert(existing, incoming, "id")
    assert once[1] == {"id": 1, "name": "Anna", "city": "Berlin"}               # merged, not replaced
    assert once[2]["name"] == "Ben"
    assert upsert(once, incoming, "id") == once                                  # idempotent
    assert existing[1]["city"] == "Munich"                                       # input not mutated


# 9
def test_top_n_per_group():
    df = pd.DataFrame({"city": ["m", "m", "m", "b", "b"], "temp": [1, 9, 5, 7, 3]})
    out = top_n_per_group(df, "city", "temp", 2)
    assert out.to_dict("records") == [
        {"city": "b", "temp": 7}, {"city": "b", "temp": 3},
        {"city": "m", "temp": 9}, {"city": "m", "temp": 5}]


def test_null_report_orders_worst_first():
    df = pd.DataFrame({"a": [1, None, None, 4], "b": [1, 2, 3, None], "c": [1, 2, 3, 4]})
    rep = null_report(df)
    assert list(rep["column"]) == ["a", "b", "c"]
    assert list(rep["nulls"]) == [2, 1, 0] and list(rep["null_pct"]) == [50.0, 25.0, 0.0]


# 10
def test_mask_email():
    assert mask_email("max.mustermann@example.com") == "m***@example.com"
    with pytest.raises(ValueError):
        mask_email("not-an-email")


def test_pseudonymize_is_deterministic_salted_and_hides_value():
    token = pseudonymize("max@example.com", salt="s3cret")
    assert token == pseudonymize("max@example.com", salt="s3cret")
    assert token != pseudonymize("max@example.com", salt="other")
    assert token != pseudonymize("anna@example.com", salt="s3cret")
    assert "max" not in token and len(token) == 16
