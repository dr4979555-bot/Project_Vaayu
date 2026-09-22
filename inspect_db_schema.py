import asyncio

from app.database import get_raw_asyncpg_connection


TABLES = [
    "weather_observations",
    "disaster_alerts",
]


async def main():
    conn = await get_raw_asyncpg_connection()

    try:
        print("\n=== DATABASE ===")

        db_info = await conn.fetchrow(
            """
            SELECT
                current_database() AS database_name,
                current_user AS username
            """
        )

        print(dict(db_info))

        print("\n=== POSTGIS ===")

        postgis = await conn.fetch(
            """
            SELECT
                extname,
                extversion
            FROM pg_extension
            WHERE extname = 'postgis'
            """
        )

        for row in postgis:
            print(dict(row))

        for table in TABLES:

            print(f"\n=== TABLE: {table} ===")

            exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                )
                """,
                table,
            )

            print("Exists:", exists)

            if not exists:
                continue

            print("\n-- COLUMNS --")

            columns = await conn.fetch(
                """
                SELECT
                    ordinal_position,
                    column_name,
                    data_type,
                    udt_name,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = $1
                ORDER BY ordinal_position
                """,
                table,
            )

            for row in columns:
                print(dict(row))

            print("\n-- CONSTRAINTS --")

            constraints = await conn.fetch(
                """
                SELECT
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                    AND tc.table_name = kcu.table_name
                WHERE tc.table_schema = 'public'
                AND tc.table_name = $1
                ORDER BY tc.constraint_name
                """,
                table,
            )

            for row in constraints:
                print(dict(row))

            print("\n-- INDEXES --")

            indexes = await conn.fetch(
                """
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename = $1
                ORDER BY indexname
                """,
                table,
            )

            for row in indexes:
                print(dict(row))

            print("\n-- ROW COUNT --")

            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM public.{table}"
            )

            print(count)

        print("\n=== DONE ===")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())