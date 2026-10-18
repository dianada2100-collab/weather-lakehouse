-- Athena DDL for the lakehouse tables.
-- Replace <BUCKET> and <PREFIX> (default prefix: weather-pipeline) before running.
-- Run the statements one by one in the Athena query editor.

CREATE DATABASE IF NOT EXISTS weather;

-- SILVER: hourly data, partitioned by city and date.
-- Partition projection means Athena computes the partitions itself:
-- no MSCK REPAIR TABLE / Glue crawler needed after each load.
CREATE EXTERNAL TABLE IF NOT EXISTS weather.silver_hourly_weather (
  ts                timestamp,
  temperature_c     double,
  precipitation_mm  double,
  wind_speed_kmh    double
)
PARTITIONED BY (city string, `date` string)
STORED AS PARQUET
LOCATION 's3://<BUCKET>/<PREFIX>/silver/hourly_weather/'
TBLPROPERTIES (
  'projection.enabled'              = 'true',
  'projection.city.type'            = 'enum',
  'projection.city.values'          = 'munich,berlin,hamburg,frankfurt,cologne',
  'projection.date.type'            = 'date',
  'projection.date.format'          = 'yyyy-MM-dd',
  'projection.date.range'           = '2024-01-01,NOW',
  'storage.location.template'       = 's3://<BUCKET>/<PREFIX>/silver/hourly_weather/city=${city}/date=${date}/'
);

-- GOLD: dimension + fact table (star schema), unpartitioned because they are small.
CREATE EXTERNAL TABLE IF NOT EXISTS weather.dim_city (
  city_key   bigint,
  city       string,
  latitude   double,
  longitude  double
)
STORED AS PARQUET
LOCATION 's3://<BUCKET>/<PREFIX>/gold/dim_city/';

CREATE EXTERNAL TABLE IF NOT EXISTS weather.fact_weather_daily (
  city_key         bigint,
  `date`           date,
  avg_temp_c       double,
  min_temp_c       double,
  max_temp_c       double,
  total_precip_mm  double,
  max_wind_kmh     double,
  hours_observed   bigint,
  is_rainy_day     boolean
)
STORED AS PARQUET
LOCATION 's3://<BUCKET>/<PREFIX>/gold/fact_weather_daily/';
