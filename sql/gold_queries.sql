-- Example analytics queries on the gold layer (Athena / Trino SQL).

-- 1) Hottest day per city (ROW_NUMBER)
WITH ranked AS (
  SELECT d.city, f.date, f.max_temp_c,
         ROW_NUMBER() OVER (PARTITION BY f.city_key ORDER BY f.max_temp_c DESC, f.date) AS rn
  FROM weather.fact_weather_daily f
  JOIN weather.dim_city d USING (city_key)
)
SELECT city, date, max_temp_c FROM ranked WHERE rn = 1 ORDER BY max_temp_c DESC;

-- 2) 3-day moving average of the daily mean temperature (window frame)
SELECT d.city, f.date, f.avg_temp_c,
       ROUND(AVG(f.avg_temp_c) OVER (
         PARTITION BY f.city_key ORDER BY f.date
         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS avg_temp_3d
FROM weather.fact_weather_daily f
JOIN weather.dim_city d USING (city_key)
ORDER BY d.city, f.date;

-- 3) Rainy-day share and total rain per city
SELECT d.city,
       COUNT(*)                                          AS days,
       SUM(CASE WHEN f.is_rainy_day THEN 1 ELSE 0 END)   AS rainy_days,
       ROUND(100.0 * AVG(CASE WHEN f.is_rainy_day THEN 1 ELSE 0 END), 1) AS rainy_pct,
       ROUND(SUM(f.total_precip_mm), 1)                  AS total_precip_mm
FROM weather.fact_weather_daily f
JOIN weather.dim_city d USING (city_key)
GROUP BY d.city
ORDER BY total_precip_mm DESC;

-- 4) Day-over-day temperature change (LAG)
SELECT d.city, f.date, f.avg_temp_c,
       ROUND(f.avg_temp_c - LAG(f.avg_temp_c) OVER (PARTITION BY f.city_key ORDER BY f.date), 2) AS delta_vs_prev_day
FROM weather.fact_weather_daily f
JOIN weather.dim_city d USING (city_key)
ORDER BY d.city, f.date;

-- 5) Data-quality probe: days with incomplete hourly data
SELECT d.city, f.date, f.hours_observed
FROM weather.fact_weather_daily f
JOIN weather.dim_city d USING (city_key)
WHERE f.hours_observed < 24
ORDER BY f.hours_observed;
