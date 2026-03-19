# =============================================================
# backend/app/data/coingecko.py
# PURPOSE:  Fetches live crypto data from CoinGecko API
#           Handles both free and Pro tier automatically
#
# FREE TIER:
#   Limit:   30 requests/minute
#   Key:     Not required (leave COINGECKO_API_KEY empty)
#   Delay:   None — data is real-time
#
# PRO TIER:
#   Limit:   500 requests/minute
#   Cost:    $129/month
#   Upgrade: Set COINGECKO_API_KEY + USE_COINGECKO_PRO=true in .env
#
# WHAT IT FETCHES:
#   - Live prices for top 20 coins
#   - 7-day sparkline data (for mini charts)
#   - Market cap, volume, 24h/7d/30d % change
#   - ATH (all time high) and ATH % change
#
# FALLBACK:
#   If CoinGecko is down or rate limited → static_demo.py
#   The fallback chain in sources.py handles this automatically
#
# AI AGENT MONITORS:
#   backend_agent → alerts if error rate > 5%
#   cost_agent    → tracks req count vs 30/min free limit
#
# LAST UPDATED: March 2026
# =============================================================

import httpx
from datetime import datetime
from typing import List, Optional

from app.core.config import settings
from app.models.market import TickerData, Market, Currency, DataSource, Timeframe
from app.data.normalize import normalize_coingecko_response


# ── CONFIG ────────────────────────────────────────────────
# CoinGecko API base URLs
COINGECKO_FREE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_PRO_URL  = "https://pro-api.coingecko.com/api/v3"

# Top 20 coins we track by default
# To add more coins: append their CoinGecko ID here
# Full list at: https://api.coingecko.com/api/v3/coins/list
DEFAULT_COIN_IDS = [
    "bitcoin", "ethereum", "solana", "binancecoin",
    "ripple", "dogecoin", "cardano", "avalanche-2",
    "chainlink", "polkadot", "uniswap", "litecoin",
    "stellar", "cosmos", "near", "tron",
    "shiba-inu", "the-open-network", "sui", "aptos"
]

# Map CoinGecko IDs to display symbols
# Add mappings here if a coin has a non-obvious symbol
COIN_SYMBOL_MAP = {
    "binancecoin": "BNB",
    "avalanche-2": "AVAX",
    "the-open-network": "TON",
    "shiba-inu": "SHIB",
}


# ── MAIN FETCH FUNCTIONS ──────────────────────────────────

async def fetch_coingecko_prices(
    symbols: List[str],
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """
    Fetch live prices for a list of crypto symbols.

    Args:
        symbols:   List of CoinGecko IDs ["bitcoin", "ethereum"]
                   OR ticker symbols ["BTC", "ETH"] — auto-converted
        timeframe: Used for % change calculation

    Returns:
        List of normalized TickerData objects

    Rate limit: 30 req/min (free), 500 req/min (pro)
    Cache TTL:  15 seconds (set in sources.py)

    UPGRADE:
        Set USE_COINGECKO_PRO=true + COINGECKO_API_KEY in .env
        for 500 req/min limit — needed at ~2K daily active users
    """
    # Convert ticker symbols to CoinGecko IDs if needed
    coin_ids = _resolve_coin_ids(symbols)
    if not coin_ids:
        coin_ids = DEFAULT_COIN_IDS

    # Build API request
    base_url = _get_base_url()
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        # Include sparkline for mini charts
        "sparkline": "true",
        # Include % changes for all timeframes
        "price_change_percentage": "24h,7d,30d",
        # Include ATH data
        "include_24hr_change": "true",
    }

    headers = _get_headers()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{base_url}/coins/markets",
            params=params,
            headers=headers
        )
        response.raise_for_status()
        raw_data = response.json()

    # Normalize raw API response → standard TickerData shape
    return [normalize_coingecko_response(coin) for coin in raw_data]


async def fetch_coingecko_heatmap(
    index: str = "crypto_top20",
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """
    Fetch data specifically formatted for the bubble heatmap.
    Same as fetch_coingecko_prices but always fetches top 20.

    Args:
        index:     "crypto_top20" | "crypto_top50" | "defi" | "layer1"
        timeframe: "1d" | "7d" | "30d"

    Returns:
        List of TickerData sorted by market cap (largest first)
    """
    # For now all indices use top 20
    # TODO: Add filtered lists (DeFi, L1, L2 etc.)
    # UPGRADE: CoinGecko Pro has category endpoints for filtered lists
    coins = await fetch_coingecko_prices(DEFAULT_COIN_IDS, timeframe)
    return sorted(coins, key=lambda x: x.market_cap or 0, reverse=True)


async def fetch_coingecko_ohlcv(
    symbol: str,
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> Optional[List[dict]]:
    """
    Fetch OHLCV candlestick data for a single coin.

    Args:
        symbol:    CoinGecko ID "bitcoin" or ticker "BTC"
        timeframe: Chart timeframe

    Returns:
        List of OHLCV dicts for candlestick chart

    NOTE:
        Free tier: max 90 days of daily candles
        Pro tier:  unlimited history
    """
    coin_id = _resolve_single_coin_id(symbol)
    days = _timeframe_to_days(timeframe)
    base_url = _get_base_url()
    headers = _get_headers()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{base_url}/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days},
            headers=headers
        )
        response.raise_for_status()
        raw = response.json()

    # CoinGecko OHLCV format: [[timestamp, open, high, low, close], ...]
    return [
        {
            "timestamp": datetime.utcfromtimestamp(candle[0] / 1000).isoformat(),
            "open":  candle[1],
            "high":  candle[2],
            "low":   candle[3],
            "close": candle[4],
            "volume": 0,  # CoinGecko OHLC endpoint doesn't include volume
            # UPGRADE: Use /coins/{id}/market_chart for volume data
        }
        for candle in raw
    ]


async def fetch_coingecko_global() -> dict:
    """
    Fetch global crypto market stats.
    Used for: total market cap, BTC dominance, fear/greed context.

    Returns: {
        total_market_cap_usd,
        btc_dominance_pct,
        active_cryptocurrencies,
        market_cap_change_24h_pct
    }
    """
    base_url = _get_base_url()
    headers = _get_headers()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{base_url}/global",
            headers=headers
        )
        response.raise_for_status()
        data = response.json().get("data", {})

    return {
        "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
        "total_volume_usd": data.get("total_volume", {}).get("usd", 0),
        "btc_dominance_pct": data.get("market_cap_percentage", {}).get("btc", 0),
        "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd", 0),
        "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
        "markets": data.get("markets", 0),
    }


# ── INTERNAL HELPERS ──────────────────────────────────────

def _get_base_url() -> str:
    """Returns Pro URL if API key set, otherwise free URL"""
    if settings.USE_COINGECKO_PRO and settings.COINGECKO_API_KEY:
        return COINGECKO_PRO_URL
    return COINGECKO_FREE_URL


def _get_headers() -> dict:
    """Returns headers including API key if available"""
    headers = {"accept": "application/json"}
    if settings.COINGECKO_API_KEY:
        # Pro tier uses x-cg-pro-api-key header
        # Free tier with key uses x-cg-demo-api-key
        key_header = "x-cg-pro-api-key" if settings.USE_COINGECKO_PRO else "x-cg-demo-api-key"
        headers[key_header] = settings.COINGECKO_API_KEY
    return headers


def _resolve_coin_ids(symbols: List[str]) -> List[str]:
    """
    Convert ticker symbols to CoinGecko IDs if needed.
    "BTC" → "bitcoin", "ETH" → "ethereum" etc.
    If already a CoinGecko ID (lowercase, no special chars), return as-is.
    """
    # Reverse lookup: symbol → id
    symbol_to_id = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
        "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin",
        "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink",
        "DOT": "polkadot", "UNI": "uniswap", "LTC": "litecoin",
        "XLM": "stellar", "ATOM": "cosmos", "NEAR": "near",
        "TRX": "tron", "SHIB": "shiba-inu", "TON": "the-open-network",
        "SUI": "sui", "APT": "aptos",
    }

    resolved = []
    for sym in symbols:
        upper = sym.upper()
        if upper in symbol_to_id:
            resolved.append(symbol_to_id[upper])
        else:
            # Assume it's already a CoinGecko ID
            resolved.append(sym.lower())

    return resolved


def _resolve_single_coin_id(symbol: str) -> str:
    """Convert single symbol to CoinGecko ID"""
    ids = _resolve_coin_ids([symbol])
    return ids[0] if ids else symbol.lower()


def _timeframe_to_days(timeframe: Timeframe) -> int:
    """Convert Timeframe enum to CoinGecko days parameter"""
    mapping = {
        Timeframe.ONE_DAY:      1,
        Timeframe.ONE_WEEK:     7,
        Timeframe.ONE_MONTH:    30,
        Timeframe.THREE_MONTHS: 90,
        Timeframe.SIX_MONTHS:  180,
        Timeframe.ONE_YEAR:    365,
        Timeframe.YTD:         365,  # Approximate
        Timeframe.FIVE_YEAR:   1825,
    }
    return mapping.get(timeframe, 7)
