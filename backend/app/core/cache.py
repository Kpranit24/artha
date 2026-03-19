# =============================================================
# backend/app/core/cache.py
# PURPOSE:  Redis cache — protects free API rate limits
#
# THE KEY INSIGHT:
#   CoinGecko free = 30 req/min
#   If 1000 users load dashboard = 1000 req/min → RATE LIMITED
#   With cache: 1000 users = 1 req per 15 seconds → FREE FOREVER
#
# CACHE LAYERS:
#   L1 (15s)    → live_prices:{symbol}
#   L2 (5min)   → computed_metrics:{index}
#   L3 (1hr)    → fundamentals:{ticker}
#   L4 (24hr)   → historical_charts:{symbol}
#   Insights    → ai_insights:{symbol} (1hr — expensive to generate)
#
# UPGRADE PATH:
#   Current: Upstash Redis free (10K commands/day)
#   1K users: Upstash Pay-as-you-go (~$10/mo)
#   10K users: Redis Cluster ($50/mo)
#   Change only REDIS_URL in .env — no code changes needed
#
# AI AGENT MONITORS THIS FILE:
#   backend_agent → tracks cache hit rate (target: >90%)
#   cost_agent    → counts commands vs Upstash free limit (10K/day)
#
# LAST UPDATED: March 2026
# =============================================================

import json
import redis.asyncio as aioredis
from typing import Any, Callable, Optional
from datetime import datetime

from app.core.config import settings


# ── REDIS CLIENT ──────────────────────────────────────────
# Single connection pool shared across all requests
# WHY POOL: Creating new connection per request is slow (~50ms)
# Pool keeps connections alive and reuses them (~1ms)
_redis_client: Optional[aioredis.Redis] = None


async def init_cache():
    """
    Initialize Redis connection on app startup.
    Called from main.py lifespan.
    """
    global _redis_client
    _redis_client = await aioredis.from_url(
        settings.REDIS_URL,
        # Connection pool settings
        max_connections=20,     # Max concurrent Redis connections
        # Timeout settings — fail fast, don't hang
        socket_connect_timeout=5,
        socket_timeout=5,
        # Retry on connection errors
        retry_on_timeout=True,
        # Decode responses as strings (not bytes)
        decode_responses=True,
    )
    # Test connection
    await _redis_client.ping()


async def close_cache():
    """Close Redis connection on app shutdown"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()


async def check_cache_health() -> bool:
    """Health check — returns True if Redis is reachable"""
    try:
        await _redis_client.ping()
        return True
    except Exception:
        return False


def get_redis() -> aioredis.Redis:
    """Get the Redis client instance"""
    if not _redis_client:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return _redis_client


# ── CORE CACHE OPERATIONS ─────────────────────────────────

async def get_with_cache(
    key: str,
    fetch_fn: Callable,
    ttl: int = None
) -> Any:
    """
    Standard cache wrapper for ALL data fetches.
    This is the ONLY way data should be fetched in this app.

    Usage:
        data = await get_with_cache(
            key="prices:crypto:bitcoin",
            fetch_fn=lambda: fetch_coingecko(["bitcoin"]),
            ttl=settings.CACHE_TTL_PRICES
        )

    TTL guide (from config.py):
        settings.CACHE_TTL_PRICES       = 15s   (live prices)
        settings.CACHE_TTL_METRICS      = 300s  (sector data)
        settings.CACHE_TTL_FUNDAMENTALS = 3600s (P/E ratios)
        settings.CACHE_TTL_HISTORICAL   = 86400s (charts)
        settings.CACHE_TTL_INSIGHTS     = 3600s (AI insights)

    NOTE TO AI AGENTS:
        Low cache hit rate (<80%) means we're hitting APIs too much.
        Check: TTLs too low? Same data being fetched with different keys?
        Alert if hit rate drops below 80% for more than 10 minutes.
    """
    if ttl is None:
        ttl = settings.CACHE_TTL_PRICES

    redis = get_redis()

    # Check cache first
    try:
        cached = await redis.get(key)
        if cached:
            # Cache HIT — return immediately, no API call needed
            _track_cache_hit(key)
            return json.loads(cached)
    except Exception as e:
        # Redis error — don't crash, just fetch fresh
        # This handles Redis being temporarily unavailable
        print(f"Cache read error for {key}: {e}")

    # Cache MISS — fetch from API
    _track_cache_miss(key)
    data = await fetch_fn()

    # Store in cache
    try:
        await redis.setex(
            key,
            ttl,
            json.dumps(data, default=_json_serializer)
        )
    except Exception as e:
        # Cache write error — return data anyway, just won't be cached
        print(f"Cache write error for {key}: {e}")

    return data


async def invalidate(key: str):
    """
    Delete a cache key immediately.
    Used when we know data has changed (e.g. after earnings).
    """
    redis = get_redis()
    await redis.delete(key)


async def invalidate_pattern(pattern: str):
    """
    Delete all cache keys matching a pattern.
    Example: invalidate_pattern("prices:crypto:*")
    
    USE CAREFULLY: This scans all keys (slow on large datasets)
    Only use for manual cache clearing, not in hot paths
    """
    redis = get_redis()
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)


async def get_cache_stats() -> dict:
    """
    Returns cache statistics for monitoring.
    Called by cost_agent every hour.
    """
    redis = get_redis()
    info = await redis.info("stats")

    total_commands = info.get("total_commands_processed", 0)
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    hit_rate = hits / (hits + misses) * 100 if (hits + misses) > 0 else 0

    return {
        "hit_rate_pct": round(hit_rate, 1),
        "total_commands": total_commands,
        "hits": hits,
        "misses": misses,
        "memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 1),
        # Upstash free tier: 10,000 commands/day
        # Alert if approaching limit
        "upstash_free_limit": 10000,
        "commands_today": total_commands,  # Approximate
    }


# ── CACHE KEY BUILDERS ────────────────────────────────────
# Consistent key naming prevents duplicate caching

def price_key(symbol: str) -> str:
    """L1 cache key for live prices"""
    return f"prices:{symbol.lower()}"


def heatmap_key(index: str, timeframe: str) -> str:
    """L1 cache key for heatmap data"""
    return f"heatmap:{index}:{timeframe}"


def metrics_key(index: str) -> str:
    """L2 cache key for computed metrics"""
    return f"metrics:{index}"


def fundamentals_key(symbol: str) -> str:
    """L3 cache key for fundamentals"""
    return f"fundamentals:{symbol.lower()}"


def historical_key(symbol: str, timeframe: str) -> str:
    """L4 cache key for historical charts"""
    return f"historical:{symbol.lower()}:{timeframe}"


def insight_key(symbol: str) -> str:
    """Cache key for AI insights (1hr TTL)"""
    return f"insight:{symbol.lower()}"


# ── INTERNAL HELPERS ──────────────────────────────────────

def _json_serializer(obj):
    """Handle non-JSON-serializable types"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _track_cache_hit(key: str):
    """Track cache hits for monitoring"""
    # TODO: Increment counter in Redis for cost_agent to read
    # Key: cache_stats:hits:{date}
    pass


def _track_cache_miss(key: str):
    """Track cache misses for monitoring"""
    # TODO: Increment counter in Redis for cost_agent to read
    # Key: cache_stats:misses:{date}
    pass
