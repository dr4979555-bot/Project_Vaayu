import asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def seed_patna():
    async with AsyncSessionLocal() as session:
        # PostGIS expects ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        query = text("""
            INSERT INTO weather_observations (
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
                'PATNA_001',
                'PATNA_AIRPORT',
                ST_SetSRID(ST_MakePoint(85.1376, 25.5941), 4326),
                31.5,
                68.0,
                0.0,
                12.5,
                'IMD_AWS',
                :now
            )
            ON CONFLICT (station_id) DO UPDATE SET
                observed_at = :now,
                temperature_c = EXCLUDED.temperature_c,
                humidity_pct = EXCLUDED.humidity_pct,
                rainfall_mm = EXCLUDED.rainfall_mm,
                wind_speed_kmh = EXCLUDED.wind_speed_kmh;
        """)
        
        await session.execute(query, {"now": datetime.now(timezone.utc)})
        await session.commit()
        print("Successfully seeded Patna Airport observation with current UTC timestamp.")

if __name__ == "__main__":
    asyncio.run(seed_patna())