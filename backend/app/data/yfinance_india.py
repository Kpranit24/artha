# =============================================================
# backend/app/data/yfinance_india.py
# PURPOSE:  Fetches India stock data (NSE/BSE) via yfinance
#           Handles the .NS (NSE) and .BO (BSE) suffix system
#
# FREE TIER:
#   Cost:   Completely free — yfinance is a Python library
#   Delay:  ~1-15 minutes on some feeds (exchange dependent)
#   Limit:  No official limit, but don't hammer it
#           Use our Redis cache (15s TTL) to avoid rate issues
#
# UPGRADE PATH:
#   Set TWELVE_DATA_KEY + USE_TWELVE_DATA=true in .env
#   Twelve Data ($39/mo) provides real-time NSE data
#   Zero code changes — sources.py routes automatically
#
# NSE SYMBOL FORMAT:
#   Append .NS to the NSE ticker: TCS → TCS.NS
#   Append .BO to the BSE ticker: TCS → TCS.BO
#   This file handles .NS by default (NSE is more liquid)
#
# NIFTY 50 CONSTITUENTS:
#   Top 20 included below — expand as needed
#   Full list: https://www.nseindia.com/market-data/live-equity-market
#
# AI AGENT MONITORS:
#   backend_agent → alerts if > 5 tickers return stale/null data
#   cost_agent    → this source is free, no spend tracking needed
#
# LAST UPDATED: March 2026
# =============================================================

import yfinance as yf
import asyncio
from datetime import datetime
from typing import List, Optional
import pandas as pd

from app.models.market import TickerData, Market, Currency, DataSource, Timeframe
from app.data.normalize import normalize_yfinance_response


# ── STOCK LISTS ───────────────────────────────────────────
# Default tickers to show on India dashboard
# Format: NSE symbol + .NS suffix
# ADDING A STOCK: append "SYMBOL.NS" to the appropriate list

NIFTY50_TOP20 = [
    "RELIANCE.NS",   # Reliance Industries
    "TCS.NS",        # Tata Consultancy Services
    "HDFCBANK.NS",   # HDFC Bank
    "ICICIBANK.NS",  # ICICI Bank
    "INFOSYS.NS",    # Infosys (listed as INFY on NSE)
    "INFY.NS",       # Infosys
    "HINDUNILVR.NS", # Hindustan Unilever
    "SBIN.NS",       # State Bank of India
    "BHARTIARTL.NS", # Bharti Airtel
    "ITC.NS",        # ITC Limited
    "KOTAKBANK.NS",  # Kotak Mahindra Bank
    "LT.NS",         # Larsen & Toubro
    "AXISBANK.NS",   # Axis Bank
    "ASIANPAINT.NS", # Asian Paints
    "MARUTI.NS",     # Maruti Suzuki
    "WIPRO.NS",      # Wipro
    "HCLTECH.NS",    # HCL Technologies
    "SUNPHARMA.NS",  # Sun Pharma
    "BAJFINANCE.NS", # Bajaj Finance
    "TATAMOTORS.NS", # Tata Motors
]

NIFTY_IT = [
    "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS",
    "TECHM.NS", "LTIM.NS", "PERSISTENT.NS", "COFORGE.NS",
    "MPHASIS.NS", "OFSS.NS"
]

NIFTY_BANK = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS"
]


# ── MAIN FETCH FUNCTIONS ──────────────────────────────────

async def fetch_yfinance_india(
    symbols: List[str],
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """
    Fetch India stock data for a list of NSE symbols.

    Args:
        symbols:   ["TCS.NS", "INFY.NS"] or ["TCS", "INFY"] (auto-adds .NS)
        timeframe: Used for OHLCV period calculation

    Returns:
        List of normalized TickerData — empty list items skipped

    NOTE:
        yfinance is synchronous — we run it in a thread pool
        to avoid blocking the async FastAPI event loop.
        This is the correct pattern for sync libraries in async code.
    """
    # Auto-add .NS suffix if missing
    nse_symbols = [_ensure_nse_suffix(s) for s in symbols]

    # Run yfinance in thread pool (it's synchronous)
    # asyncio.to_thread available in Python 3.9+
    loop = asyncio.get_event_loop()
    raw_data = await loop.run_in_executor(
        None,  # Use default thread pool
        lambda: _fetch_yfinance_sync(nse_symbols, timeframe)
    )

    # Normalize and filter out None values
    results = []
    for symbol, data in raw_data.items():
        if data is not None:
            ticker_data = normalize_yfinance_response(symbol, data)
            if ticker_data:
                results.append(ticker_data)

    return results


async def fetch_nifty50(timeframe: Timeframe = Timeframe.ONE_DAY) -> List[TickerData]:
    """
    Fetch the top 20 Nifty 50 constituents.
    Used for the India heatmap and default market view.
    """
    return await fetch_yfinance_india(NIFTY50_TOP20, timeframe)


async def fetch_nifty_index(
    index_name: str = "nifty50",
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> List[TickerData]:
    """
    Fetch data for a specific Nifty index.

    Args:
        index_name: "nifty50" | "nifty_it" | "nifty_bank"
        timeframe:  Chart timeframe

    Returns:
        List of TickerData for that index

    TODO: Add more indices (Nifty Pharma, Nifty Auto, etc.)
    """
    index_map = {
        "nifty50":    NIFTY50_TOP20,
        "nifty_it":   NIFTY_IT,
        "nifty_bank": NIFTY_BANK,
    }
    symbols = index_map.get(index_name, NIFTY50_TOP20)
    return await fetch_yfinance_india(symbols, timeframe)


async def fetch_india_ohlcv(
    symbol: str,
    timeframe: Timeframe = Timeframe.ONE_MONTH
) -> List[dict]:
    """
    Fetch OHLCV candlestick data for a single India stock.

    Args:
        symbol:    "TCS.NS" or "TCS" (auto-adds .NS)
        timeframe: Chart period

    Returns:
        List of OHLCV dicts for candlestick chart
    """
    nse_symbol = _ensure_nse_suffix(symbol)
    period, interval = _timeframe_to_yfinance_params(timeframe)

    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(
        None,
        lambda: _fetch_ohlcv_sync(nse_symbol, period, interval)
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


# ── SYNCHRONOUS HELPERS (run in thread pool) ──────────────

def _fetch_yfinance_sync(
    symbols: List[str],
    timeframe: Timeframe
) -> dict:
    """
    Synchronous yfinance fetch — runs in thread pool.
    DO NOT call this directly — use fetch_yfinance_india() instead.

    Uses yfinance's batch download for efficiency.
    Single API call for all symbols = much faster than individual calls.
    """
    results = {}

    try:
        # Batch download — much more efficient than individual .info calls
        # yfinance fetches all symbols in one request
        tickers = yf.Tickers(" ".join(symbols))

        for symbol in symbols:
            try:
                ticker = tickers.tickers[symbol]
                info = ticker.fast_info  # fast_info is faster than .info

                # Get today's history for price data
                hist = ticker.history(period="2d")

                if hist.empty:
                    results[symbol] = None
                    continue

                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest

                results[symbol] = {
                    "info": {
                        "shortName": getattr(info, "exchange", symbol),
                        "currency": "INR",
                        "sector": None,  # fast_info doesn't include sector
                        "marketCap": getattr(info, "market_cap", None),
                        "trailingPE": getattr(info, "pe_ratio", None),
                        "beta": getattr(info, "beta", None),
                        "dividendYield": None,
                    },
                    "latest": {
                        "open":   float(latest.get("Open", 0)),
                        "high":   float(latest.get("High", 0)),
                        "low":    float(latest.get("Low", 0)),
                        "close":  float(latest.get("Close", 0)),
                        "volume": float(latest.get("Volume", 0)),
                    },
                    "prev_close": float(prev.get("Close", latest.get("Close", 0))),
                    "symbol": symbol,
                }

            except Exception as e:
                # Individual ticker failed — skip it, don't crash batch
                print(f"yfinance error for {symbol}: {e}")
                results[symbol] = None

    except Exception as e:
        print(f"yfinance batch error: {e}")

    return results


def _fetch_ohlcv_sync(symbol: str, period: str, interval: str):
    """Synchronous OHLCV fetch — runs in thread pool"""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period, interval=interval)
    except Exception as e:
        print(f"yfinance OHLCV error for {symbol}: {e}")
        return None


# ── INTERNAL HELPERS ──────────────────────────────────────

def _ensure_nse_suffix(symbol: str) -> str:
    """
    Ensures symbol has .NS suffix for NSE.
    TCS → TCS.NS
    TCS.NS → TCS.NS (unchanged)
    TCS.BO → TCS.BO (BSE, unchanged)
    """
    if "." in symbol:
        return symbol.upper()
    return f"{symbol.upper()}.NS"


def _timeframe_to_yfinance_params(timeframe: Timeframe) -> tuple[str, str]:
    """
    Convert Timeframe to yfinance (period, interval) params.
    Returns: (period, interval)
    """
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
