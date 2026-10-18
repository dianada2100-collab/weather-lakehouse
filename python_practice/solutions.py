"""Ten typical data-engineering Python tasks with clean, tested solutions.

Each function mirrors something you do in real pipelines: de-duplication, flattening JSON,
batching, retries, log parsing, schema validation, incremental loads, upserts, pandas
reporting and GDPR-style pseudonymisation. Try to solve them yourself first (see README.md),
then compare.
"""
from __future__ import annotations

import functools
import hashlib
import re
import time
from collections import Counter
from typing import Any, Callable, Iterable, Iterator

import pandas as pd


# 1) De-duplication: keep the latest record per key ------------------------------------------
def dedupe_latest(records: list[dict], key: str, ts_key: str) -> list[dict]:
    """Keep, per `key`, the record with the largest `ts_key` (later input wins ties).
    The output keeps the order in which each key first appeared."""
    best: dict[Any, dict] = {}
    for rec in records:
        k = rec[key]
        if k not in best or rec[ts_key] >= best[k][ts_key]:
            best[k] = rec
    return list(best.values())          # dicts keep first-insertion order of keys


# 2) Flatten nested JSON -----------------------------------------------------------------------
def flatten_json(obj: Any, sep: str = ".", _prefix: str = "") -> dict[str, Any]:
    """{'a': {'b': 1}, 'c': [10, 20]} -> {'a.b': 1, 'c.0': 10, 'c.1': 20}"""
    flat: dict[str, Any] = {}
    if isinstance(obj, dict):
        items: Iterable[tuple[str, Any]] = ((str(k), v) for k, v in obj.items())
    elif isinstance(obj, list):
        items = ((str(i), v) for i, v in enumerate(obj))
    else:
        return {_prefix: obj} if _prefix else {}
    for k, v in items:
        path = f"{_prefix}{sep}{k}" if _prefix else k
        if isinstance(v, (dict, list)) and v:
            flat.update(flatten_json(v, sep, path))
        else:
            flat[path] = v              # scalars and empty containers are leaves
    return flat


# 3) Batching with a generator ------------------------------------------------------------------
def chunked(iterable: Iterable[Any], size: int) -> Iterator[list[Any]]:
    """Yield lists of at most `size` items without loading everything into memory."""
    if size < 1:
        raise ValueError("size must be >= 1")
    batch: list[Any] = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


# 4) Retry decorator with exponential backoff ---------------------------------------------------
def retry(
    max_attempts: int = 3,
    backoff_s: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
):
    """Retry the wrapped function on the given exceptions; re-raise after the last attempt."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions:
                    if attempt == max_attempts:
                        raise
                    sleep(backoff_s * 2 ** (attempt - 1))
        return wrapper
    return decorator


# 5) Log parsing with regex ----------------------------------------------------------------------
_LOG_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>[A-Z]+) (?P<service>[\w.-]+): (?P<message>.*)$"
)


def parse_log_line(line: str) -> dict[str, str] | None:
    """'2025-01-01 12:00:00 ERROR payment-service: timeout' -> dict, or None if malformed."""
    match = _LOG_RE.match(line.strip())
    return match.groupdict() if match else None


def count_by_level(lines: Iterable[str]) -> Counter:
    return Counter(p["level"] for line in lines if (p := parse_log_line(line)))


def top_error_services(lines: Iterable[str], n: int = 3) -> list[tuple[str, int]]:
    errors = Counter(p["service"] for line in lines
                     if (p := parse_log_line(line)) and p["level"] == "ERROR")
    return sorted(errors.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


# 6) Record validation against a simple schema ---------------------------------------------------
def validate_record(record: dict, schema: dict[str, dict]) -> list[str]:
    """schema = {'id': {'type': int, 'required': True}, ...}. Returns a list of error messages."""
    errors: list[str] = []
    for field, rule in schema.items():
        if field not in record or record[field] is None:
            if rule.get("required", False):
                errors.append(f"{field}: missing required field")
            continue
        value = record[field]
        # bool is a subclass of int in Python - do not accept True/False as an int
        if not isinstance(value, rule["type"]) or (rule["type"] is int and isinstance(value, bool)):
            errors.append(f"{field}: expected {rule['type'].__name__}, got {type(value).__name__}")
    for field in record.keys() - schema.keys():
        errors.append(f"{field}: unexpected field")
    return sorted(errors)


# 7) Incremental load with a watermark -----------------------------------------------------------
def incremental_filter(records: list[dict], watermark: Any, ts_key: str) -> tuple[list[dict], Any]:
    """Return (records newer than watermark, new watermark). The watermark never moves back."""
    new = [r for r in records if r[ts_key] > watermark]
    return new, max([watermark, *(r[ts_key] for r in new)])


# 8) Idempotent upsert -------------------------------------------------------------------------
def upsert(existing: dict[Any, dict], incoming: list[dict], key: str) -> dict[Any, dict]:
    """Merge `incoming` into `existing` by key without mutating the input.
    Running it twice with the same input gives the same result (idempotent)."""
    merged = dict(existing)
    for rec in incoming:
        merged[rec[key]] = {**merged.get(rec[key], {}), **rec}
    return merged


# 9) pandas: top-N per group and a null report ----------------------------------------------------
def top_n_per_group(df: pd.DataFrame, group_col: str, sort_col: str, n: int) -> pd.DataFrame:
    return (df.sort_values([group_col, sort_col], ascending=[True, False], kind="stable")
              .groupby(group_col, sort=False).head(n)
              .reset_index(drop=True))


def null_report(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column with null count and percentage, worst columns first."""
    report = pd.DataFrame({"nulls": df.isna().sum(), "null_pct": (df.isna().mean() * 100).round(1)})
    return report.sort_values(["nulls"], ascending=False, kind="stable").rename_axis("column").reset_index()


# 10) GDPR helpers: masking and pseudonymisation ---------------------------------------------------
def mask_email(email: str) -> str:
    """'max.mustermann@example.com' -> 'm***@example.com'"""
    local, sep, domain = email.partition("@")
    if not sep or not local:
        raise ValueError(f"not an email address: {email!r}")
    return f"{local[0]}***@{domain}"


def pseudonymize(value: str, salt: str) -> str:
    """Deterministic, non-reversible token: the same person always gets the same token
    (so joins still work), but the original value cannot be read back. Keep the salt secret."""
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:16]
