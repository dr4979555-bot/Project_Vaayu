-- =========================================================
-- VAAYU PRODUCTION DATABASE SCHEMA
-- PostgreSQL + PostGIS
-- =========================================================

BEGIN;


-- =========================================================
-- 1. PostGIS
-- =========================================================

CREATE SCHEMA IF NOT EXISTS extensions;

CREATE EXTENSION IF NOT EXISTS postgis
WITH SCHEMA extensions;


-- =========================================================
-- 2. Weather Observations
-- =========================================================

CREATE TABLE IF NOT EXISTS public.weather_observations (

    station_id TEXT PRIMARY KEY,

    station_name TEXT NOT NULL,

    location extensions.geometry(
        Point,
        4326
    ) NOT NULL,

    temperature_c DOUBLE PRECISION,

    humidity_pct DOUBLE PRECISION,

    rainfall_mm DOUBLE PRECISION DEFAULT 0.0,

    wind_speed_kmh DOUBLE PRECISION,

    source TEXT,

    observed_at TIMESTAMPTZ NOT NULL

);


-- Spatial index for nearest-station queries
CREATE INDEX IF NOT EXISTS idx_weather_observations_location
ON public.weather_observations
USING GIST (location);


-- Useful timestamp index
CREATE INDEX IF NOT EXISTS idx_weather_observations_observed_at
ON public.weather_observations (observed_at);


-- =========================================================
-- 3. Disaster Alerts
-- =========================================================

CREATE TABLE IF NOT EXISTS public.disaster_alerts (

    alert_id BIGSERIAL PRIMARY KEY,

    sender TEXT NOT NULL,

    sent_at TIMESTAMPTZ NOT NULL,

    status TEXT NOT NULL,

    severity TEXT NOT NULL,

    event_category TEXT NOT NULL,

    headline TEXT NOT NULL,

    description TEXT,

    instruction TEXT,

    affected_polygon extensions.geometry(
        Polygon,
        4326
    ) NOT NULL,

    signature_ecdsa TEXT NOT NULL

);


-- Spatial index for alert-radius queries
CREATE INDEX IF NOT EXISTS idx_disaster_alerts_polygon
ON public.disaster_alerts
USING GIST (affected_polygon);


-- Active-alert lookup index
CREATE INDEX IF NOT EXISTS idx_disaster_alerts_status_sent_at
ON public.disaster_alerts (
    status,
    sent_at DESC
);


-- =========================================================
-- 4. Basic validation indexes
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_disaster_alerts_category
ON public.disaster_alerts (event_category);

CREATE INDEX IF NOT EXISTS idx_weather_observations_station
ON public.weather_observations (station_name);


COMMIT;