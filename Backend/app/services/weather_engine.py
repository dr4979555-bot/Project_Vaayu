import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import NowcastResponse

logger = logging.getLogger("WeatherGPT.WeatherEngine")


# ---------------------------------------------------------------------------
# IMD Rainfall Intensity Classification (mm/hr thresholds)
# Source: India Meteorological Department colour-coded warning system
# ---------------------------------------------------------------------------
_RAINFALL_THRESHOLDS = [
    (2.5,  "Light"),
    (7.5,  "Moderate"),
    (35.5, "Heavy"),
    (64.4, "Very Heavy"),
    (float("inf"), "Extremely Heavy"),  # Red Warning
]


class WeatherEngine:
    """
    Deterministic Meteorological Ground-Truth Engine.
    Executes PostGIS nearest-neighbour lookups with metric geography distance,
    rainfall intensity classification, and spatial alert intersection queries.
    """

    # ------------------------------------------------------------------
    # 1. Nearest Station Observation (existing)
    # ------------------------------------------------------------------
    @classmethod
    async def get_nearest_station_observation(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        max_radius_km: float = 100.0,
        enable_realtime_fallback: bool = True,
    ) -> Optional[NowcastResponse]:
        """
        Retrieves meteorological observations using a multi-tiered strategy:
        1. Local PostGIS database lookup for IMD AWS stations within max_radius_km
        2. Real-time ECMWF/GFS assimilated observation via Open-Meteo if no station is in range
        """
        from app.services.realtime_weather import RealtimeWeatherService

        try:
            # PostGIS requires (longitude, latitude) → (X, Y)
            # Explicitly prefix with extensions. for Supabase compatibility
            query = text("""
                SELECT
                    station_id,
                    station_name,
                    temperature_c,
                    humidity_pct,
                    rainfall_mm,
                    wind_speed_kmh,
                    source,
                    observed_at,
                    extensions.ST_Y(location::extensions.geometry) AS latitude,
                    extensions.ST_X(location::extensions.geometry) AS longitude,
                    ROUND((
                        extensions.ST_Distance(
                            location::extensions.geography,
                            extensions.ST_SetSRID(
                                extensions.ST_MakePoint(:lon, :lat), 4326
                            )::extensions.geography
                        ) / 1000.0
                    )::numeric, 2) AS distance_km
                FROM public.weather_observations
                WHERE extensions.ST_DWithin(
                    location::extensions.geography,
                    extensions.ST_SetSRID(
                        extensions.ST_MakePoint(:lon, :lat), 4326
                    )::extensions.geography,
                    :max_radius_meters
                )
                ORDER BY
                    extensions.ST_Distance(
                        location::extensions.geography,
                        extensions.ST_SetSRID(
                            extensions.ST_MakePoint(:lon, :lat), 4326
                        )::extensions.geography
                    )
                LIMIT 1;
            """)

            result = await db.execute(
                query,
                {
                    "lat": float(latitude),
                    "lon": float(longitude),
                    "max_radius_meters": float(max_radius_km * 1000.0),
                },
            )
            row = result.mappings().first()

            if row:
                return NowcastResponse(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    station_name=str(row["station_name"]),
                    distance_km=float(row["distance_km"]),
                    temperature_c=float(row["temperature_c"]) if row["temperature_c"] is not None else None,
                    humidity_pct=float(row["humidity_pct"]) if row["humidity_pct"] is not None else None,
                    rainfall_mm=float(row["rainfall_mm"]) if row["rainfall_mm"] is not None else 0.0,
                    wind_speed_kmh=float(row["wind_speed_kmh"]) if row["wind_speed_kmh"] is not None else None,
                    source=str(row["source"]),
                    timestamp=(
                        row["observed_at"].isoformat()
                        if hasattr(row["observed_at"], "isoformat")
                        else str(row["observed_at"])
                    ),
                    active_alert=None,
                )

            logger.info(
                f"No database station found within {max_radius_km}km of ({latitude}, {longitude}). "
                "Falling back to real-time meteorological engine."
            )

        except Exception as e:
            logger.warning(f"PostGIS nearest-station lookup failed, falling back to real-time engine: {e}")

        # Tier 2: Real-time ECMWF/GFS meteorological observation
        if enable_realtime_fallback:
            live = await RealtimeWeatherService.fetch_realtime_weather(
                latitude=latitude,
                longitude=longitude,
            )
            if live:
                logger.info(f"Retrieved real-time weather from Open-Meteo for ({latitude}, {longitude})")
                return NowcastResponse(
                    latitude=latitude,
                    longitude=longitude,
                    station_name=f"Realtime Grid Cell ({latitude:.2f}°N, {longitude:.2f}°E)",
                    distance_km=0.0,
                    temperature_c=live.get("temperature_c"),
                    apparent_temperature_c=live.get("apparent_temperature_c"),
                    humidity_pct=live.get("humidity_pct"),
                    rainfall_mm=live.get("rainfall_mm", 0.0),
                    wind_speed_kmh=live.get("wind_speed_kmh"),
                    weather_condition=live.get("weather_condition"),
                    precipitation_probability_pct=live.get("precipitation_probability_pct"),
                    surface_pressure_hpa=live.get("surface_pressure_hpa"),
                    source=live.get("source", "Open-Meteo (ECMWF/GFS)"),
                    timestamp=live.get("observed_at"),
                    active_alert=None,
                )

        return None

    # ------------------------------------------------------------------
    # 2. IMD Rainfall Intensity Classifier
    # ------------------------------------------------------------------
    @staticmethod
    def classify_rainfall_intensity(mm: float) -> str:
        """
        Classifies rainfall intensity per IMD colour-coded warning thresholds.
        Input  : rainfall in mm/hr
        Returns: human-readable intensity label
        """
        for threshold, label in _RAINFALL_THRESHOLDS:
            if mm < threshold:
                return label
        return "Extremely Heavy"

    # ------------------------------------------------------------------
    # 3. Active CAP Alerts in Spatial Radius
    # ------------------------------------------------------------------
    @classmethod
    async def get_active_alerts_in_radius(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """
        Returns all active CAP v1.2 disaster alerts whose polygon overlaps
        or is within `radius_km` of the given point.
        Uses PostGIS ST_DWithin on geography for metric distance accuracy.
        """
        try:
            query = text("""
                SELECT
                    alert_id::text,
                    sender,
                    severity,
                    event_category,
                    headline,
                    description,
                    instruction,
                    sent_at::text,
                    status
                FROM public.disaster_alerts
                WHERE
                    status = 'Actual'
                    AND extensions.ST_DWithin(
                        affected_polygon::extensions.geography,
                        extensions.ST_SetSRID(
                            extensions.ST_MakePoint(:lon, :lat), 4326
                        )::extensions.geography,
                        :radius_meters
                    )
                ORDER BY sent_at DESC;
            """)

            result = await db.execute(
                query,
                {
                    "lat": float(latitude),
                    "lon": float(longitude),
                    "radius_meters": float(radius_km * 1000.0),
                },
            )
            rows = result.mappings().all()
            return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Active alerts spatial lookup failed: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # 4. Route–Alert Intersection Check
    # ------------------------------------------------------------------
    @classmethod
    async def check_route_alert_intersection(
        cls,
        db: AsyncSession,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> List[Dict[str, Any]]:
        """
        Uses PostGIS ST_MakeLine + ST_Intersects to determine which active
        CAP alert polygons the straight-line route between origin and
        destination passes through.

        Note: This is a straight-line approximation. For real road-network
        routing, integrate pgRouting or an external OSRM service.
        """
        try:
            query = text("""
                SELECT
                    alert_id::text,
                    sender,
                    severity,
                    event_category,
                    headline,
                    description,
                    instruction,
                    sent_at::text,
                    status
                FROM public.disaster_alerts
                WHERE
                    status = 'Actual'
                    AND extensions.ST_Intersects(
                        affected_polygon,
                        extensions.ST_MakeLine(
                            extensions.ST_SetSRID(
                                extensions.ST_MakePoint(:orig_lon, :orig_lat), 4326
                            ),
                            extensions.ST_SetSRID(
                                extensions.ST_MakePoint(:dest_lon, :dest_lat), 4326
                            )
                        )
                    )
                ORDER BY severity DESC, sent_at DESC;
            """)

            result = await db.execute(
                query,
                {
                    "orig_lat": float(origin_lat),
                    "orig_lon": float(origin_lon),
                    "dest_lat": float(dest_lat),
                    "dest_lon": float(dest_lon),
                },
            )
            rows = result.mappings().all()
            return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Route-alert intersection query failed: {e}", exc_info=True)
            return []