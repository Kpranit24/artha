# =============================================================
# backend/app/data/static_demo.py
# PURPOSE:  Hardcoded demo data — fallback of last resort
#           Also used when DEMO_MODE=true in .env
#
# WHEN USED:
#   1. All live APIs are down or rate limited
#   2. DEMO_MODE=true in .env (e.g. for UI development)
#   3. During testing to avoid hitting real APIs
#   4. Cold start before first API fetch
#
# HOW TO USE DEMO MODE:
#   Set DEMO_MODE=true in .env
#   All data fetches return this static data
#   No API calls made — great for UI development
#
# KEEPING DEMO DATA FRESH:
#   Update prices here roughly every month
#   Or they'll look obviously wrong when demoing
#   Last updated: March 2026
#
# AI AGENT MONITORS:
#   backend_agent → alerts if demo data is returned for > 30 min
#                   in production (means live sources are broken)
#
# LAST UPDATED: March 2026
# =============================================================

from datetime import datetime
from typing import List

from app.models.market import TickerData, Market, Currency, DataSource, Timeframe


# ── DEMO PRICES (update monthly) ─────────────────────────

_DEMO_CRYPTO = [
    {"symbol": "BTC",  "name": "Bitcoin",   "price": 83120, "change_1d": -1.18, "change_7d": -3.2,  "market_cap": 1638000000000, "volume_24h": 42000000000},
    {"symbol": "ETH",  "name": "Ethereum",  "price": 3241,  "change_1d": -0.84, "change_7d": -2.1,  "market_cap": 390000000000,  "volume_24h": 18000000000},
    {"symbol": "SOL",  "name": "Solana",    "price": 142,   "change_1d": -2.1,  "change_7d": -5.4,  "market_cap": 65000000000,   "volume_24h": 3500000000},
    {"symbol": "BNB",  "name": "BNB",       "price": 598,   "change_1d": 0.3,   "change_7d": 1.2,   "market_cap": 87000000000,   "volume_24h": 1800000000},
    {"symbol": "XRP",  "name": "XRP",       "price": 2.14,  "change_1d": 1.4,   "change_7d": 8.2,   "market_cap": 123000000000,  "volume_24h": 4200000000},
    {"symbol": "DOGE", "name": "Dogecoin",  "price": 0.18,  "change_1d": -0.5,  "change_7d": -2.8,  "market_cap": 26000000000,   "volume_24h": 1100000000},
    {"symbol": "ADA",  "name": "Cardano",   "price": 0.78,  "change_1d": 0.9,   "change_7d": 3.1,   "market_cap": 27000000000,   "volume_24h": 820000000},
    {"symbol": "AVAX", "name": "Avalanche", "price": 35.4,  "change_1d": -1.8,  "change_7d": -6.2,  "market_cap": 14500000000,   "volume_24h": 480000000},
    {"symbol": "LINK", "name": "Chainlink", "price": 18.2,  "change_1d": 2.4,   "change_7d": 7.8,   "market_cap": 11200000000,   "volume_24h": 620000000},
    {"symbol": "DOT",  "name": "Polkadot",  "price": 9.8,   "change_1d": -0.6,  "change_7d": -1.4,  "market_cap": 14800000000,   "volume_24h": 340000000},
]

_DEMO_INDIA = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "price": 2910, "change_1d": -0.3,  "market_cap": 19700000000000, "pe_ratio": 28.4},
    {"symbol": "TCS",      "name": "Tata Consultancy",    "price": 3780, "change_1d": 0.8,   "market_cap": 13700000000000, "pe_ratio": 24.1},
    {"symbol": "HDFCBANK", "name": "HDFC Bank",           "price": 1635, "change_1d": -0.6,  "market_cap": 12400000000000, "pe_ratio": 18.2},
    {"symbol": "INFY",     "name": "Infosys",             "price": 1842, "change_1d": 1.4,   "market_cap": 7650000000000,  "pe_ratio": 24.1},
    {"symbol": "ICICIBANK","name": "ICICI Bank",           "price": 1089, "change_1d": 0.4,   "market_cap": 7700000000000,  "pe_ratio": 17.8},
    {"symbol": "HINDUNILVR","name": "HUL",                "price": 2340, "change_1d": -0.2,  "market_cap": 5490000000000,  "pe_ratio": 52.1},
    {"symbol": "SBIN",     "name": "State Bank India",    "price": 752,  "change_1d": -0.8,  "market_cap": 6710000000000,  "pe_ratio": 9.2},
    {"symbol": "WIPRO",    "name": "Wipro",               "price": 488,  "change_1d": 2.1,   "market_cap": 2560000000000,  "pe_ratio": 22.8},
    {"symbol": "HCLTECH",  "name": "HCL Technologies",    "price": 1620, "change_1d": 0.7,   "market_cap": 4400000000000,  "pe_ratio": 21.8},
    {"symbol": "TATAMOTORS","name": "Tata Motors",        "price": 812,  "change_1d": 1.2,   "market_cap": 3000000000000,  "pe_ratio": 7.2},
]

_DEMO_US = [
    {"symbol": "AAPL",  "name": "Apple",       "price": 218,   "change_1d": 0.5,   "market_cap": 3350000000000, "pe_ratio": 34.2},
    {"symbol": "MSFT",  "name": "Microsoft",   "price": 415,   "change_1d": 0.9,   "market_cap": 3080000000000, "pe_ratio": 36.2},
    {"symbol": "NVDA",  "name": "NVIDIA",      "price": 874,   "change_1d": 3.2,   "market_cap": 2140000000000, "pe_ratio": 38.4},
    {"symbol": "GOOGL", "name": "Alphabet",    "price": 182,   "change_1d": 0.4,   "market_cap": 2260000000000, "pe_ratio": 24.8},
    {"symbol": "AMZN",  "name": "Amazon",      "price": 196,   "change_1d": 0.6,   "market_cap": 2080000000000, "pe_ratio": 35.4},
    {"symbol": "META",  "name": "Meta",        "price": 512,   "change_1d": 1.8,   "market_cap": 1390000000000, "pe_ratio": 27.1},
    {"symbol": "TSLA",  "name": "Tesla",       "price": 174,   "change_1d": -2.4,  "market_cap": 554000000000,  "pe_ratio": 55.2},
    {"symbol": "JPM",   "name": "JPMorgan",    "price": 228,   "change_1d": -0.3,  "market_cap": 658000000000,  "pe_ratio": 12.8},
    {"symbol": "AMD",   "name": "AMD",         "price": 168,   "change_1d": 2.1,   "market_cap": 272000000000,  "pe_ratio": 44.1},
    {"symbol": "INFY",  "name": "Infosys ADR", "price": 22.4,  "change_1d": 1.4,   "market_cap": 93000000000,   "pe_ratio": 24.1},
]


# ── FETCH FUNCTIONS ───────────────────────────────────────

async def fetch_demo_crypto(
    symbols: List[str] = None,
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """Returns static crypto demo data — no API calls"""
    data = _DEMO_CRYPTO
    if symbols:
        # Filter to requested symbols
        upper = [s.upper() for s in symbols]
        data = [d for d in _DEMO_CRYPTO if d["symbol"] in upper]
    return [_to_ticker(d, Market.CRYPTO, Currency.USD) for d in data]


async def fetch_demo_india_stocks(
    symbols: List[str] = None,
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """Returns static India stock demo data — no API calls"""
    data = _DEMO_INDIA
    if symbols:
        clean = [s.replace(".NS", "").replace(".BO", "").upper() for s in symbols]
        data = [d for d in _DEMO_INDIA if d["symbol"] in clean]
    return [_to_ticker(d, Market.INDIA, Currency.INR) for d in data]


async def fetch_demo_us_stocks(
    symbols: List[str] = None,
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """Returns static US stock demo data — no API calls"""
    data = _DEMO_US
    if symbols:
        upper = [s.upper() for s in symbols]
        data = [d for d in _DEMO_US if d["symbol"] in upper]
    return [_to_ticker(d, Market.US, Currency.USD) for d in data]


# ── INTERNAL BUILDER ──────────────────────────────────────

def _to_ticker(data: dict, market: Market, currency: Currency) -> TickerData:
    """Convert demo dict → TickerData"""
    return TickerData(
        symbol=data["symbol"],
        name=data["name"],
        market=market,
        currency=currency,
        price=float(data["price"]),
        change_1d=data.get("change_1d"),
        change_7d=data.get("change_7d"),
        volume_24h=data.get("volume_24h"),
        market_cap=data.get("market_cap"),
        pe_ratio=data.get("pe_ratio"),
        source=DataSource.STATIC_DEMO,
        is_live=False,            # Always mark demo data as not live
        fetched_at=datetime.utcnow(),
        delayed_by_seconds=0,
    )
