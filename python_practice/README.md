# Python practice for data engineering

Ten small tasks that mirror real pipeline code. `solutions.py` contains clean solutions, and
`test_solutions.py` (19 tests) shows how to test them. **Try each task yourself first**: write your
own function in a scratch file and run the tests against it.

| # | Task | Signature (in `solutions.py`) | Real-world use |
|---|------|-------------------------------|----------------|
| 1 | Keep the newest record per key | `dedupe_latest(records, key, ts_key)` | CDC / duplicate events |
| 2 | Flatten nested JSON | `flatten_json(obj, sep=".")` | API responses to tables |
| 3 | Process in batches (generator) | `chunked(iterable, size)` | bulk inserts, API limits |
| 4 | Retry with exponential backoff | `@retry(max_attempts, backoff_s)` | flaky network calls |
| 5 | Parse and aggregate log lines | `parse_log_line`, `count_by_level`, `top_error_services` | monitoring |
| 6 | Validate records against a schema | `validate_record(record, schema)` | data quality at ingestion |
| 7 | Incremental load with a watermark | `incremental_filter(records, watermark, ts_key)` | delta loads |
| 8 | Idempotent upsert | `upsert(existing, incoming, key)` | safe re-runs |
| 9 | pandas: top-N per group, null report | `top_n_per_group`, `null_report` | profiling, reporting |
| 10 | Masking and pseudonymisation | `mask_email`, `pseudonymize` | GDPR / data protection |

Run: `python -m pytest python_practice -v`

**Interview angle:** for every task be ready to explain (a) edge cases (ties, empty input, `None`),
(b) time/memory complexity, and (c) how it behaves when the job is run twice (idempotency).
