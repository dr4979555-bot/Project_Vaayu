import socket
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

import re
from urllib.parse import unquote

def _parse_db_url(raw_url: str):
    # Regex matches: postgresql[+asyncpg]://user:password@host[:port]/database
    # Handles passwords containing '@' by matching the LAST @ before host:port
    pattern = re.compile(
        r"^(?:(?P<scheme>[^:]+)://)?(?P<user>[^:]+):(?P<password>.+)@(?P<host>[^@:/]+)(?::(?P<port>\d+))?/(?P<db>[^?]+)"
    )
    match = pattern.match(raw_url)
    if match:
        user = match.group("user")
        password = unquote(match.group("password"))
        host = match.group("host")
        port = int(match.group("port") or 5432)
        db = match.group("db")
        return user, password, host, port, db

    u = make_url(raw_url)
    return u.username, u.password, u.host, u.port or 5432, u.database

_db_user, _db_password, _db_host, _db_port, _db_name = _parse_db_url(settings.DATABASE_URL)


async def get_raw_asyncpg_connection():
    """
    Creates an authenticated asyncpg connection by pre-resolving the host
    using AF_INET to eliminate Windows Errno 11003 / NAT64 routing issues.
    """
    # pyrefly: ignore [missing-import]
    import asyncpg

    target_host = _db_host
    try:
        # Prefer IPv4 on Windows — eliminates Errno 11003
        addrs = socket.getaddrinfo(_db_host, _db_port, socket.AF_INET, socket.SOCK_STREAM)
        if not addrs:
            addrs = socket.getaddrinfo(_db_host, _db_port, 0, socket.SOCK_STREAM)
        if addrs:
            target_host = addrs[0][4][0]
    except Exception:
        pass

    return await asyncpg.connect(
        user=_db_user,
        password=_db_password,
        database=_db_name,
        host=target_host,
        port=_db_port,
        ssl="require",
        statement_cache_size=0,
        server_settings={"search_path": "public, extensions"},
        timeout=15,
    )


# Pass async_creator so SQLAlchemy uses our verified connection factory
engine = create_async_engine(
    settings.DATABASE_URL,
    async_creator=get_raw_asyncpg_connection,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    """Dependency for injecting database sessions into route handlers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()