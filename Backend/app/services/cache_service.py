import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any
# pyrefly: ignore [missing-import]
from redis.asyncio import from_url, Redis
from app.config import settings

logger = logging.getLogger("WeatherGPT.CacheService")


class CacheService:
    """
    Tier-1 Spatiotemporal & Semantic Cache.
    Quantizes coordinates (~1.1 km tiles) and time (15-minute buckets).
    """

    _client: Optional[Redis] = None

    @classmethod
    async def get_client(cls) -> Optional[Redis]:
        """Lazy initialization of the asynchronous Redis client with SSL bypass."""
        if cls._client is None and settings.UPSTASH_REDIS_URL:
            try:
                raw_url = settings.UPSTASH_REDIS_URL.strip().strip("'\"")

                if raw_url.startswith("redis://"):
                    raw_url = "rediss://" + raw_url[len("redis://"):]
                elif not raw_url.startswith("rediss://"):
                    raw_url = f"rediss://{raw_url}"

                cls._client = from_url(
                    raw_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=10.0,
                    socket_timeout=10.0,
                    ssl_cert_reqs="none",
                )
                await cls._client.ping()
                logger.info("Successfully connected to Upstash Redis cache.")
            except Exception as e:
                logger.warning(f"Redis initialization failed: {e}. Running cache-bypassed.")
                cls._client = None
        return cls._client

    @staticmethod
    def generate_tile_key(lat: float, lon: float, query: str, language: str) -> str:
        lat_tile = round(lat, 2)
        lon_tile = round(lon, 2)
        time_bucket = int(datetime.now(timezone.utc).timestamp() // 900)
        clean_query = query.strip().lower()
        # Deterministic MD5 hash so keys match across different processes and server restarts
        query_hash = hashlib.md5(clean_query.encode("utf-8")).hexdigest()[:8]

        return f"weathergpt:cache:{lat_tile}:{lon_tile}:{time_bucket}:{language}:{query_hash}"

    @classmethod
    async def get(cls, key: str) -> Optional[dict]:
        try:
            client = await cls.get_client()
            if not client:
                return None
            val = await client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.debug(f"Cache lookup failed for key {key}: {e}")
        return None

    @classmethod
    async def set(cls, key: str, value: Any, ttl_seconds: int = 900, expire: Optional[int] = None) -> None:
        try:
            client = await cls.get_client()
            if not client:
                return
            ttl = expire if expire is not None else ttl_seconds
            serialized = value if isinstance(value, str) else json.dumps(value)
            await client.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.debug(f"Cache write failed for key {key}: {e}")