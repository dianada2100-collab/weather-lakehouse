"""Run the gold-layer analytics queries locally with DuckDB (no AWS needed).

    python3 -m pip install duckdb
    python3 scripts/query_local.py            # runs all queries
    python3 scripts/query_local.py 2          # runs only query 2

Reads the Parquet files the pipeline wrote to ./data (override with LOCAL_ROOT).
"""
from __future__ import annotations

import os
import sys

import duckdb

ROOT = os.getenv("LOCAL_ROOT", "data")

QUERIES = {
    "1) Hottest day per city": """
        WITH ranked AS (
          SELECT d.city, f.date, f.max_temp_c,
                 ROW_NUMBER() OVER (PARTITION BY f.city_key ORDER BY f.max_temp_c DESC, f.date) AS rn
          FROM fact_weather_daily f JOIN dim_city d USING (city_key)
        )
        SELECT city, date, max_temp_c FROM ranked WHERE rn = 1 ORDER BY max_temp_c DESC
    """,
    "2) 3-day moving average of the daily mean temperature (first 10 rows)": """
        SELECT d.city, f.date, f.avg_temp_c,
               ROUND(AVG(f.avg_temp_c) OVER (
                 PARTITION BY f.city_key ORDER BY f.date
                 ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS avg_temp_3d
        FROM fact_weather_daily f JOIN dim_city d USING (city_key)
        ORDER BY d.city, f.date
        LIMIT 10
    """,
    "3) Rainy days and total rain per city": """
        SELECT d.city,
               COUNT(*) AS days,
               SUM(CASE WHEN f.is_rainy_day THEN 1 ELSE 0 END) AS rainy_days,
               ROUND(100.0 * AVG(CASE WHEN f.is_rainy_day THEN 1 ELSE 0 END), 1) AS rainy_pct,
               ROUND(SUM(f.total_precip_mm), 1) AS total_precip_mm
        FROM fact_weather_daily f JOIN dim_city d USING (city_key)
        GROUP BY d.city ORDER BY total_precip_mm DESC
    """,
    "4) Day-over-day temperature change (first 10 rows)": """
        SELECT d.city, f.date, f.avg_temp_c,
               ROUND(f.avg_temp_c - LAG(f.avg_temp_c) OVER (PARTITION BY f.city_key ORDER BY f.date), 2)
                 AS delta_vs_prev_day
        FROM fact_weather_daily f JOIN dim_city d USING (city_key)
        ORDER BY d.city, f.date
        LIMIT 10
    """,
    "5) Data-quality probe: days with incomplete hourly data": """
        SELECT d.city, f.date, f.hours_observed
        FROM fact_weather_daily f JOIN dim_city d USING (city_key)
        WHERE f.hours_observed < 24
        ORDER BY f.hours_observed
    """,
    "6) Silver check: hours and mean temperature per city": """
        SELECT city, COUNT(*) AS hours, ROUND(AVG(temperature_c), 1) AS avg_temp
        FROM silver GROUP BY city ORDER BY avg_temp
    """,
}


def connect(root: str = ROOT) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.sql(f"""
        CREATE VIEW dim_city AS SELECT * FROM read_parquet('{root}/gold/dim_city/data.parquet');
        CREATE VIEW fact_weather_daily AS
            SELECT * FROM read_parquet('{root}/gold/fact_weather_daily/data.parquet');
        CREATE VIEW silver AS
            SELECT * FROM read_parquet('{root}/silver/hourly_weather/*/*/*.parquet', hive_partitioning = true);
    """)
    return con


def main(argv: list[str]) -> int:
    selected = {k: v for k, v in QUERIES.items() if not argv or k.startswith(f"{argv[0]})")}
    if not selected:
        print(f"No query {argv[0]!r}. Available: 1-{len(QUERIES)}")
        return 1
    con = connect()
    for title, sql in selected.items():
        print(f"\n== {title}")
        print(con.sql(sql))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
