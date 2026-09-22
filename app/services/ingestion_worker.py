import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.realtime_weather import RealtimeWeatherService

logger = logging.getLogger("WeatherGPT.IngestionWorker")

# Primary Indian Meteorological Hubs & Observation Stations
PRIMARY_MET_STATIONS: List[Dict[str, Any]] = [
    {"id": "DELHI_001", "name": "DELHI_SAFDARJUNG", "lat": 28.6139, "lon": 77.2090},
    {"id": "MUMBAI_001", "name": "MUMBAI_COLABA", "lat": 19.0760, "lon": 72.8777},
    {"id": "KOLKATA_001", "name": "KOLKATA_ALIPORE", "lat": 22.5726, "lon": 88.3639},
    {"id": "CHENNAI_001", "name": "CHENNAI_MEENAMBAKKAM", "lat": 13.0827, "lon": 80.2707},
    {"id": "BENGALURU_001", "name": "BENGALURU_HAL", "lat": 12.9716, "lon": 77.5946},
    {"id": "PATNA_001", "name": "PATNA_AIRPORT", "lat": 25.5941, "lon": 85.1376},
    {"id": "HYDERABAD_001", "name": "HYDERABAD_BEGUMPET", "lat": 17.3850, "lon": 78.4867},
    {"id": "AHMEDABAD_001", "name": "AHMEDABAD_AIRPORT", "lat": 23.0225, "lon": 72.5714},
    {"id": "PUNE_001", "name": "PUNE_SHIVAJINAGAR", "lat": 18.5204, "lon": 73.8567},
    {"id": "NAGPUR_001", "name": "NAGPUR_SONEGAON", "lat": 21.1458, "lon": 79.0882},
    {"id": "JAIPUR_001", "name": "JAIPUR_SANGANER", "lat": 26.9124, "lon": 75.7873},
    {"id": "LUCKNOW_001", "name": "LUCKNOW_AMAUSI", "lat": 26.8467, "lon": 80.9462},
    {"id": "BHOPAL_001", "name": "BHOPAL_BAIRAGARH", "lat": 23.2599, "lon": 77.4126},
    {"id": "KOCHI_001", "name": "KOCHI_NAVAL_AIR", "lat": 9.9312, "lon": 76.2673},
    {"id": "GUWAHATI_001", "name": "GUWAHATI_BORJHAR", "lat": 26.1445, "lon": 91.7362},
    {"id": "BHUBANESWAR_001", "name": "BHUBANESWAR_BPIA", "lat": 20.2961, "lon": 85.8245},
    {"id": "SRINAGAR_001", "name": "SRINAGAR_AERODROME", "lat": 34.0837, "lon": 74.7973},
    {"id": "SHIMLA_001", "name": "SHIMLA_RIDGE", "lat": 31.1048, "lon": 77.1734},
]


class MeteorologicalIngestionWorker:
    """
    Priority 2: Live Meteorological Ingestion Worker (Background Cron).
    Continuously ingests live feeds from Open-Meteo & IMD AWS stations into
    PostGIS spatial table `weather_observations`.
    """

    _running: bool = False
    _worker_task: asyncio.Task | None = None

    @classmethod
    async def ingest_single_station(cls, session, station: Dict[str, Any]) -> bool:
        """Fetches live meteorological observation and upserts into PostGIS."""
        try:
            live = await RealtimeWeatherService.fetch_realtime_weather(
                latitude=station["lat"],
                longitude=station["lon"],
            )
            if not live:
                logger.warning(f"No live data returned for station {station['name']}")
                return False

            query = text("""
                INSERT INTO public.weather_observations (
                    station_id,
                    station_name,
                    location,
                    temperature_c,
                    humidity_pct,
                    rainfall_mm,
                    wind_speed_kmh,
                    source,
                    observed_at
                ) VALUES (
                    :station_id,
                    :station_name,
                    extensions.ST_SetSRID(extensions.ST_MakePoint(:lon, :lat), 4326),
                    :temperature_c,
                    :humidity_pct,
                    :rainfall_mm,
                    :wind_speed_kmh,
                    :source,
                    :observed_at
                )
                ON CONFLICT (station_id) DO UPDATE SET
                    temperature_c = EXCLUDED.temperature_c,
                    humidity_pct = EXCLUDED.humidity_pct,
                    rainfall_mm = EXCLUDED.rainfall_mm,
                    wind_speed_kmh = EXCLUDED.wind_speed_kmh,
                    source = EXCLUDED.source,
                    observed_at = EXCLUDED.observed_at;
            """)

            await session.execute(
                query,
                {
                    "station_id": station["id"],
                    "station_name": station["name"],
                    "lat": float(station["lat"]),
                    "lon": float(station["lon"]),
                    "temperature_c": live.get("temperature_c"),
                    "humidity_pct": live.get("humidity_pct"),
                    "rainfall_mm": live.get("rainfall_mm", 0.0),
                    "wind_speed_kmh": live.get("wind_speed_kmh"),
                    "source": live.get("source", "Open-Meteo (ECMWF/GFS)"),
                    "observed_at": datetime.now(timezone.utc),
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to ingest station {station['name']}: {e}")
            return False

    @classmethod
    async def run_ingestion_cycle(cls) -> Dict[str, Any]:
        """Executes a full ingestion cycle across all primary meteorological stations."""
        logger.info(f"Starting meteorological ingestion cycle across {len(PRIMARY_MET_STATIONS)} stations...")
        success_count = 0
        failed_count = 0

        async with AsyncSessionLocal() as session:
            for station in PRIMARY_MET_STATIONS:
                ok = await cls.ingest_single_station(session, station)
                if ok:
                    success_count += 1
                else:
                    failed_count += 1
            await session.commit()

        logger.info(f"Ingestion cycle complete. Succeeded: {success_count}, Failed: {failed_count}")
        return {
            "status": "completed",
            "stations_attempted": len(PRIMARY_MET_STATIONS),
            "succeeded": success_count,
            "failed": failed_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    async def _worker_loop(cls):
        """Continuous background loop running periodically."""
        interval_secs = max(settings.INGESTION_INTERVAL_MINUTES * 60, 60)
        logger.info(f"Meteorological Ingestion Worker loop started (interval: {interval_secs}s).")

        # Initial run on startup
        try:
            await cls.run_ingestion_cycle()
        except Exception as e:
            logger.error(f"Error in initial ingestion cycle: {e}")

        while cls._running:
            try:
                await asyncio.sleep(interval_secs)
                if not cls._running:
                    break
                await cls.run_ingestion_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ingestion worker loop: {e}")
                await asyncio.sleep(30)

    @classmethod
    def start_background_worker(cls):
        """Starts the background worker task if not already running."""
        if not cls._running:
            cls._running = True
            cls._worker_task = asyncio.create_task(cls._worker_loop())
            logger.info("MeteorologicalIngestionWorker background task spawned.")

    @classmethod
    async def stop_background_worker(cls):
        """Stops the background worker gracefully."""
        cls._running = False
        if cls._worker_task:
            cls._worker_task.cancel()
            try:
                await cls._worker_task
            except asyncio.CancelledError:
                pass
            cls._worker_task = None
            logger.info("MeteorologicalIngestionWorker background task stopped.")
