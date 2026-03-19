# =============================================================
# backend/app/core/database.py
# PURPOSE:  Database connection, session management, base model
#
# USES:     SQLAlchemy async + asyncpg driver
# DB:       Postgres (Supabase in production, local in dev)
#
# UPGRADE PATH:
#   TimescaleDB extension for market_snapshots time-series:
#   Run: CREATE EXTENSION IF NOT EXISTS timescaledb;
#   Then: SELECT create_hypertable('market_snapshots','snapshot_at');
#
# LAST UPDATED: March 2026
# =============================================================

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from typing import AsyncGenerator

from app.core.config import settings


# ── ENGINE ────────────────────────────────────────────────
# asyncpg driver = fastest async Postgres driver available
# Convert standard postgresql:// to postgresql+asyncpg://
def _make_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _make_async_url(settings.DATABASE_URL),
    pool_size=10,          # Max connections in pool
    max_overflow=20,       # Extra connections beyond pool_size
    pool_pre_ping=True,    # Test connections before use
    echo=settings.is_development,  # Log SQL in dev only
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── BASE MODEL ────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── LIFECYCLE ─────────────────────────────────────────────
async def init_db():
    """Called on startup — verifies DB connection"""
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


async def check_db_health() -> bool:
    """Health check — returns True if DB reachable"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ── DEPENDENCY ────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a DB session per request.
    Usage:
        @router.get("/")
        async def route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
