# =============================================================
# backend/app/data/sources.py
# PURPOSE:  Central fallback chain for all data sources
#           If primary source fails, automatically tries next
#
# HOW IT WORKS:
#   Every market has a chain of sources.
#   data_agent always calls get_ticker_data() or get_heatmap_data()
#   This file handles routing to the right source + fallback.
#
# ADDING A PAID SOURCE:
#   1. Add your API key to .env
#   2. Implement fetch function in data/polygon.py etc.
#   3. Add to the TOP of the relevant chain below
#   4. No changes needed anywhere else
#
# AI AGENT MONITORS THIS FILE:
#   backend_agent → tracks which source is being used
#   cost_agent    → tracks API call counts vs free tier limits
#
# LAST UPDATED: March 2026
# =============================================================

import asyncio
from datetime import datetime
from typing import List, Optional

from app.core.config import settings
from app.core.cache import get_with_cache
from app.models.market import TickerData, HeatmapData, OHLCVData, Timeframe, DataSource


# ── FALLBACK CHAIN CONFIG ─────────────────────────────────
# Order = priority (first = try first)
# Each entry: (source_name, fetch_function, is_available)

def _build_crypto_chain():
    """
    Crypto data fallback chain.
    Add Polygon/Coinbase to top when keys are available.
    """
    from app.data.coingecko import fetch_coingecko_prices, fetch_coingecko_heatmap
    from app.data.static_demo import fetch_demo_crypto

    chain = []

    # CoinGecko Pro (paid) — fastest, highest limits
    # UPGRADE: Set COINGECKO_API_KEY + USE_COINGECKO_PRO=true
    if settings.USE_COINGECKO_PRO and settings.COINGECKO_API_KEY:
        chain.append(("coingecko_pro", fetch_coingecko_prices, True))

    # CoinGecko Free (default) — 30 req/min, good enough for launch
    chain.append(("coingecko_free", fetch_coingecko_prices, True))

    # Static demo — always works, used as last resort
    # Also used when DEMO_MODE=true in .env
    chain.append(("static_demo", fetch_demo_crypto, True))

    return chain


def _build_us_stocks_chain():
    """
    US stocks fallback chain.
    Add Polygon to top when key is available.
    """
    from app.data.yahoo import fetch_yahoo_prices
    from app.data.alpha_vantage import fetch_alpha_vantage_prices
    from app.data.static_demo import fetch_demo_us_stocks

    chain = []

    # Polygon.io (paid) — institutional grade, real-time
    # UPGRADE: Set POLYGON_API_KEY + USE_POLYGON=true
    if settings.USE_POLYGON and settings.POLYGON_API_KEY:
        from app.data.polygon import fetch_polygon_prices
        chain.append(("polygon", fetch_polygon_prices, True))

    # Yahoo Finance (free, unofficial) — good enough for most use cases
    # RISK: Unofficial API may break — Alpha Vantage is the fallback
    chain.append(("yahoo_finance", fetch_yahoo_prices, True))

    # Alpha Vantage (free, 5 req/min) — backup when Yahoo is down
    if settings.ALPHA_VANTAGE_KEY:
        chain.append(("alpha_vantage", fetch_alpha_vantage_prices, True))

    chain.append(("static_demo", fetch_demo_us_stocks, True))

    return chain


def _build_india_stocks_chain():
    """
    India stocks fallback chain.
    yfinance handles NSE/BSE via .NS and .BO suffixes.
    """
    from app.data.yfinance_india import fetch_yfinance_india
    from app.data.static_demo import fetch_demo_india_stocks

    chain = []

    # Twelve Data (paid) — best NSE/BSE real-time data
    # UPGRADE: Set TWELVE_DATA_KEY + USE_TWELVE_DATA=true
    if settings.USE_TWELVE_DATA and settings.TWELVE_DATA_KEY:
        from app.data.twelve_data import fetch_twelve_data_india
        chain.append(("twelve_data", fetch_twelve_data_india, True))

    # yfinance (free) — handles NSE via TCS.NS, INFY.NS etc.
    # Slight delay (~1 minute) but free and reliable
    chain.append(("yfinance", fetch_yfinance_india, True))

    chain.append(("static_demo", fetch_demo_india_stocks, True))

    return chain


# ── MAIN DATA FETCHER ─────────────────────────────────────

async def get_prices(
    symbols: List[str],
    market: str,
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """
    Fetch prices for a list of symbols with automatic fallback.

    Args:
        symbols:   ["BTC", "ETH"] or ["TCS.NS", "INFY.NS"] or ["AAPL", "NVDA"]
        market:    "crypto" | "india" | "us"
        timeframe: How far back to look

    Returns:
        List of TickerData — always returns something (worst case: demo data)

    NOTE TO AI AGENTS:
        If this returns DataSource.STATIC_DEMO for more than 1 hour,
        something is wrong with the primary data source.
        Alert and investigate.
    """

    # Use demo data if DEMO_MODE is on
    if settings.DEMO_MODE:
        return await _fetch_with_fallback(
            symbols, [("static_demo", _get_demo_fn(market), True)]
        )

    # Check cache first
    cache_key = f"prices:{market}:{','.join(sorted(symbols))}:{timeframe}"
    cached = await get_with_cache(
        key=cache_key,
        fetch_fn=lambda: _fetch_prices(symbols, market, timeframe),
        ttl=settings.CACHE_TTL_PRICES
    )
    return cached


async def _fetch_prices(
    symbols: List[str],
    market: str,
    timeframe: Timeframe
) -> List[TickerData]:
    """
    Internal: tries each source in the fallback chain.
    Returns first successful result.
    """
    chains = {
        "crypto": _build_crypto_chain(),
        "us": _build_us_stocks_chain(),
        "india": _build_india_stocks_chain(),
    }

    chain = chains.get(market, [])
    last_error = None

    for source_name, fetch_fn, is_available in chain:
        if not is_available:
            continue
        try:
            result = await fetch_fn(symbols, timeframe)
            if result:
                # Log which source we used (for monitoring)
                _log_source_used(market, source_name)
                return result
        except Exception as e:
            last_error = e
            # Log the failure but continue to next source
            print(f"Source {source_name} failed: {e}. Trying next...")
            continue

    # All sources failed — this should never happen
    # static_demo is always last and always works
    raise Exception(f"All data sources failed for {market}: {last_error}")


def _log_source_used(market: str, source: str):
    """
    Logs which data source was used.
    cost_agent reads these logs to track API usage vs free limits.
    """
    # TODO: Write to Redis for cost_agent to read
    # Format: source_usage:{market}:{date} = {source: count}
    pass


def _get_demo_fn(market: str):
    """Returns the demo data function for a market"""
    from app.data.static_demo import (
        fetch_demo_crypto,
        fetch_demo_us_stocks,
        fetch_demo_india_stocks
    )
    return {
        "crypto": fetch_demo_crypto,
        "us": fetch_demo_us_stocks,
        "india": fetch_demo_india_stocks,
    }.get(market, fetch_demo_crypto)
