import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import asyncpg


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "production_schema.sql"


def clean_database_url(url: str) -> str:
    parsed = urlparse(url)

    query_parts = []

    for item in parsed.query.split("&"):
        if not item:
            continue

        key, _, value = item.partition("=")

        if key.lower() != "sslmode":
            query_parts.append(item)

    clean_query = "&".join(query_parts)

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            parsed.fragment,
        )
    )


async def main():
    database_url = os.getenv("RENDER_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "RENDER_DATABASE_URL is not set."
        )

    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(
            f"Missing schema file: {SCHEMA_FILE}"
        )

    schema_sql = SCHEMA_FILE.read_text(
        encoding="utf-8"
    )

    database_url = clean_database_url(database_url)

    print("Connecting to Render PostgreSQL...")

    conn = await asyncpg.connect(
        database_url,
        ssl="require",
    )

    try:
        print("Connected successfully.")
        print("Applying production schema...")

        await conn.execute(schema_sql)

        print("Schema applied successfully.")

        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN (
                  'weather_observations',
                  'disaster_alerts'
              )
            ORDER BY table_name;
            """
        )

        print("\nTables found:")
        for row in tables:
            print(f"- public.{row['table_name']}")

        postgis = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_extension
                WHERE extname = 'postgis'
            );
            """
        )

        print(f"\nPostGIS enabled: {postgis}")

    finally:
        await conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
