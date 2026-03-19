# =============================================================
# backend/app/data/yahoo.py
# PURPOSE:  Fetches US stock data via Yahoo Finance (unofficial)
#
# FREE TIER:
#   Cost:  Free — unofficial Yahoo Finance API
#   Risk:  Unofficial = may break without notice
#           Alpha Vantage is the fallback (sources.py handles this)
#   Limit: No official limit — use Redis cache to be safe
#
# UPGRADE PATH:
#   Set POLYGON_API_KEY + USE_POLYGON=true in .env
#   Polygon.io ($199/mo) provides real-time NYSE/NASDAQ data
#   sources.py routes to Polygon automatically when key is set
#
# US STOCKS TRACKED:
#   S&P 500 top 10 + popular tech + India-listed ADRs
#   Edit US_DEFAULT_SYMBOLS to change defaults
#
# AI AGENT MONITORS:
#   backend_agent → alerts if Yahoo returns errors 3x in a row
#                   triggers switch to Alpha Vantage fallback
#
# LAST UPDATED: March 2026
# =============================================================

import httpx
import asyncio
import yfinance as yf
from datetime import datetime
from typing import List, Optional

from app.models.market import TickerData, Market, Currency, DataSource, Timeframe
from app.data.normalize import normalize_yahoo_response


# ── DEFAULT SYMBOLS ───────────────────────────────────────
# US stocks shown by default
# Add/remove symbols here to change the default watchlist

US_DEFAULT_SYMBOLS = [
    # Mega-cap tech
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "NVDA",   # NVIDIA
    "GOOGL",  # Alphabet
    "AMZN",   # Amazon
    "META",   # Meta
    "TSLA",   # Tesla
    # Finance
    "JPM",    # JPMorgan
    "BRK-B",  # Berkshire Hathaway
    # Semiconductors
    "AMD",    # AMD
    "INTC",   # Intel
    "TSM",    # TSMC (India investors watch this)
    # India-connected US stocks
    "WIT",    # Wipro ADR
    "INFY",   # Infosys ADR (same ticker on NYSE)
]

# S&P 500 sectors for heatmap
SP500_SECTORS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Healthcare": ["JNJ", "UNH", "PFE", "ABBV"],
    "Artha":    ["JPM", "BAC", "WFC", "GS"],
    "Consumer":   ["AMZN", "TSLA", "HD", "MCD"],
    "Energy":     ["XOM", "CVX", "COP"],
}


# ── MAIN FETCH FUNCTIONS ──────────────────────────────────

async def fetch_yahoo_prices(
    symbols: List[str],
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """
    Fetch US stock prices via yfinance (Yahoo Finance backend).

    Args:
        symbols:   ["AAPL", "NVDA", "MSFT"] — standard US tickers
        timeframe: Used for % change calculation

    Returns:
        List of normalized TickerData

    NOTE:
        yfinance is synchronous — wrapped in thread pool
        Same pattern as yfinance_india.py for consistency
    """
    if not symbols:
        symbols = US_DEFAULT_SYMBOLS

    loop = asyncio.get_event_loop()
    raw_data = await loop.run_in_executor(
        None,
        lambda: _fetch_yahoo_sync(symbols)
    )

    results = []
    for symbol, data in raw_data.items():
        if data:
            ticker_data = normalize_yahoo_response(symbol, data)
            if ticker_data:
                results.append(ticker_data)

    return results


async def fetch_us_heatmap(
    index: str = "sp500_top20",
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """
    Fetch US stocks formatted for bubble heatmap.

    Args:
        index:     "sp500_top20" | "nasdaq100_top20" | "tech"
        timeframe: Chart timeframe

    Returns:
        List sorted by market cap (largest first)
    """
    index_map = {
        "sp500_top20":   US_DEFAULT_SYMBOLS[:20],
        "nasdaq100_top20": ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","ASML","COST"],
        "tech":          SP500_SECTORS["Technology"],
    }
    symbols = index_map.get(index, US_DEFAULT_SYMBOLS)
    stocks = await fetch_yahoo_prices(symbols, timeframe)
    return sorted(stocks, key=lambda x: x.market_cap or 0, reverse=True)


async def fetch_yahoo_ohlcv(
    symbol: str,
    timeframe: Timeframe = Timeframe.ONE_MONTH
) -> List[dict]:
    """
    Fetch OHLCV candlestick data for a US stock.

    Args:
        symbol:    "AAPL", "NVDA" etc.
        timeframe: Chart period

    Returns:
        List of OHLCV dicts
    """
    period, interval = _timeframe_to_params(timeframe)
    loop = asyncio.get_event_loop()

    df = await loop.run_in_executor(
        None,
        lambda: _fetch_ohlcv_sync(symbol, period, interval)
    )

    if df is None or df.empty:
        return []

    return [
        {
            "timestamp": str(row.name.isoformat()),
            "open":   float(row["Open"]),
            "high":   float(row["High"]),
            "low":    float(row["Low"]),
            "close":  float(row["Close"]),
            "volume": float(row["Volume"]),
        }
        for _, row in df.iterrows()
    ]


# ── SYNCHRONOUS HELPERS ───────────────────────────────────

def _fetch_yahoo_sync(symbols: List[str]) -> dict:
    """
    Synchronous batch fetch — runs in thread pool.
    Uses yfinance batch download (1 request for all symbols).
    """
    results = {}

    try:
        tickers = yf.Tickers(" ".join(symbols))

        for symbol in symbols:
            try:
                ticker = tickers.tickers[symbol]
                info = ticker.fast_info
                hist = ticker.history(period="2d")

                if hist.empty:
                    results[symbol] = None
                    continue

                latest  = hist.iloc[-1]
                prev    = hist.iloc[-2] if len(hist) > 1 else latest

                # Get week change
                hist_1w = ticker.history(period="7d")
                week_open = float(hist_1w.iloc[0]["Close"]) if not hist_1w.empty else None

                results[symbol] = {
                    "symbol": symbol,
                    "info": {
                        "shortName": getattr(info, "exchange", symbol),
                        "currency": "USD",
                        "marketCap": getattr(info, "market_cap", None),
                        "trailingPE": getattr(info, "pe_ratio", None),
                        "beta": getattr(info, "beta", None),
                    },
                    "latest": {
                        "open":   float(latest.get("Open", 0)),
                        "high":   float(latest.get("High", 0)),
                        "low":    float(latest.get("Low", 0)),
                        "close":  float(latest.get("Close", 0)),
                        "volume": float(latest.get("Volume", 0)),
                    },
                    "prev_close": float(prev.get("Close", 0)),
                    "week_open":  week_open,
                }

            except Exception as e:
                print(f"Yahoo error for {symbol}: {e}")
                results[symbol] = None

    except Exception as e:
        print(f"Yahoo batch error: {e}")

    return results


def _fetch_ohlcv_sync(symbol: str, period: str, interval: str):
    """Synchronous OHLCV fetch"""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period, interval=interval)
    except Exception as e:
        print(f"Yahoo OHLCV error for {symbol}: {e}")
        return None


def _timeframe_to_params(timeframe: Timeframe) -> tuple[str, str]:
    """Convert Timeframe to yfinance (period, interval)"""
    mapping = {
        Timeframe.ONE_DAY:      ("2d",  "5m"),
        Timeframe.ONE_WEEK:     ("7d",  "1h"),
        Timeframe.ONE_MONTH:    ("1mo", "1d"),
        Timeframe.THREE_MONTHS: ("3mo", "1d"),
        Timeframe.SIX_MONTHS:  ("6mo", "1wk"),
        Timeframe.ONE_YEAR:    ("1y",  "1wk"),
        Timeframe.YTD:         ("ytd", "1d"),
        Timeframe.FIVE_YEAR:   ("5y",  "1mo"),
    }
    return mapping.get(timeframe, ("1mo", "1d"))
