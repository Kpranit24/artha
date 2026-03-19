# =============================================================
# backend/app/data/normalize.py
# PURPOSE:  Converts raw API responses → standard TickerData
#           Single place where all data normalization happens
#
# WHY THIS EXISTS:
#   CoinGecko, Yahoo Finance, NSE, Twelve Data all return
#   different field names, formats, and currencies.
#   This file is the "translation layer" that makes them all
#   look identical to the rest of the app.
#
#   If CoinGecko changes their API → fix ONLY normalize_coingecko_response()
#   If Yahoo changes → fix ONLY normalize_yahoo_response()
#   Nothing else in the app needs to change.
#
# ADDING A NEW DATA SOURCE:
#   1. Create normalize_{source_name}_response() function below
#   2. Import it in data/{source_name}.py
#   3. Call it after the API fetch
#   4. It must return Optional[TickerData]
#
# AI AGENT MONITORS:
#   backend_agent → alerts if normalization returns None > 10% of time
#                   (usually means API changed their response format)
#
# LAST UPDATED: March 2026
# =============================================================

from datetime import datetime
from typing import Optional
import math

from app.models.market import (
    TickerData, Market, Currency, DataSource, Timeframe
)


# ── COINGECKO NORMALIZER ──────────────────────────────────

def normalize_coingecko_response(raw: dict) -> Optional[TickerData]:
    """
    Normalize a single CoinGecko /coins/markets item → TickerData.

    CoinGecko response shape:
    {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": 83120,
        "price_change_percentage_24h": -1.18,
        "price_change_percentage_7d_in_currency": -3.2,
        "price_change_percentage_30d_in_currency": 12.4,
        "market_cap": 1638000000000,
        "total_volume": 42000000000,
        "sparkline_in_7d": {"price": [...]},
        "ath": 108000,
        "ath_change_percentage": -23.0,
        ...
    }

    Returns None if required fields are missing.
    """
    if not raw or "current_price" not in raw:
        return None

    try:
        return TickerData(
            # Identity
            symbol=raw.get("symbol", "").upper(),
            name=raw.get("name", ""),
            market=Market.CRYPTO,
            currency=Currency.USD,

            # Price
            price=float(raw.get("current_price", 0)),
            price_high=raw.get("high_24h"),
            price_low=raw.get("low_24h"),

            # Changes
            change_1d=_safe_float(raw.get("price_change_percentage_24h")),
            change_7d=_safe_float(raw.get("price_change_percentage_7d_in_currency")),
            change_30d=_safe_float(raw.get("price_change_percentage_30d_in_currency")),

            # Volume and market cap
            volume_24h=_safe_float(raw.get("total_volume")),
            market_cap=_safe_float(raw.get("market_cap")),

            # Sparkline (7-day price history for mini charts)
            sparkline=raw.get("sparkline_in_7d", {}).get("price", []),

            # ATH
            ath=_safe_float(raw.get("ath")),
            ath_change_pct=_safe_float(raw.get("ath_change_percentage")),

            # Metadata
            source=DataSource.COINGECKO,
            is_live=True,
            fetched_at=datetime.utcnow(),
            delayed_by_seconds=0,
        )
    except Exception as e:
        print(f"CoinGecko normalize error for {raw.get('symbol', '?')}: {e}")
        return None


# ── YFINANCE NORMALIZER (India .NS stocks) ────────────────

def normalize_yfinance_response(symbol: str, raw: dict) -> Optional[TickerData]:
    """
    Normalize yfinance response → TickerData for India stocks.

    yfinance raw shape (from yfinance_india.py):
    {
        "symbol": "TCS.NS",
        "info": {
            "shortName": "NSE",
            "currency": "INR",
            "marketCap": 1400000000000,
            "trailingPE": 24.1,
            "beta": 0.8,
        },
        "latest": {
            "open": 3760, "high": 3800, "low": 3740,
            "close": 3780, "volume": 2500000
        },
        "prev_close": 3750,
    }

    Returns None if essential price data is missing.
    """
    if not raw or not raw.get("latest"):
        return None

    latest = raw["latest"]
    info   = raw.get("info", {})
    prev   = raw.get("prev_close", latest.get("close", 0))
    price  = latest.get("close", 0)

    if not price or price == 0:
        return None

    # Calculate % change from previous close
    change_1d = ((price - prev) / prev * 100) if prev else 0

    # Clean display symbol (remove .NS suffix for display)
    display_symbol = symbol.replace(".NS", "").replace(".BO", "")

    try:
        return TickerData(
            # Identity
            symbol=display_symbol,
            name=info.get("shortName", display_symbol),
            market=Market.INDIA,
            currency=Currency.INR,

            # Price
            price=float(price),
            price_open=_safe_float(latest.get("open")),
            price_high=_safe_float(latest.get("high")),
            price_low=_safe_float(latest.get("low")),
            price_close=float(price),

            # Changes
            change_1d=round(change_1d, 2),
            change_7d=None,    # TODO: fetch 7d history for this
            change_30d=None,   # TODO: fetch 30d history for this

            # Volume and market cap
            volume_24h=_safe_float(latest.get("volume")),
            market_cap=_safe_float(info.get("marketCap")),

            # Fundamentals
            pe_ratio=_safe_float(info.get("trailingPE")),
            beta=_safe_float(info.get("beta")),

            # Metadata
            source=DataSource.YFINANCE,
            is_live=True,
            fetched_at=datetime.utcnow(),
            # yfinance has slight delay — mark as such
            delayed_by_seconds=60,
        )
    except Exception as e:
        print(f"yfinance normalize error for {symbol}: {e}")
        return None


# ── YAHOO NORMALIZER (US stocks) ──────────────────────────

def normalize_yahoo_response(symbol: str, raw: dict) -> Optional[TickerData]:
    """
    Normalize Yahoo Finance response → TickerData for US stocks.
    Same data source as yfinance — slightly different raw shape.
    """
    if not raw or not raw.get("latest"):
        return None

    latest    = raw["latest"]
    info      = raw.get("info", {})
    prev      = raw.get("prev_close", 0)
    week_open = raw.get("week_open")
    price     = latest.get("close", 0)

    if not price or price == 0:
        return None

    change_1d = ((price - prev) / prev * 100) if prev else 0
    change_7d = ((price - week_open) / week_open * 100) if week_open else None

    try:
        return TickerData(
            symbol=symbol.upper(),
            name=info.get("shortName", symbol),
            market=Market.US,
            currency=Currency.USD,

            price=float(price),
            price_open=_safe_float(latest.get("open")),
            price_high=_safe_float(latest.get("high")),
            price_low=_safe_float(latest.get("low")),
            price_close=float(price),

            change_1d=round(change_1d, 2),
            change_7d=round(change_7d, 2) if change_7d else None,

            volume_24h=_safe_float(latest.get("volume")),
            market_cap=_safe_float(info.get("marketCap")),
            pe_ratio=_safe_float(info.get("trailingPE")),
            beta=_safe_float(info.get("beta")),

            source=DataSource.YAHOO,
            is_live=True,
            fetched_at=datetime.utcnow(),
            delayed_by_seconds=0,
        )
    except Exception as e:
        print(f"Yahoo normalize error for {symbol}: {e}")
        return None


# ── HEATMAP BUBBLE BUILDER ────────────────────────────────

def build_heatmap_bubble(ticker: TickerData, rank: int, max_cap: float) -> dict:
    """
    Convert TickerData → HeatmapBubble format for Plotly chart.

    Args:
        ticker:   Normalized TickerData
        rank:     Market cap rank (1 = largest)
        max_cap:  Largest market cap in dataset (for relative sizing)

    Returns:
        Dict with x, y, size, color for Plotly Scattergl
    """
    change = ticker.change_1d or 0
    is_up  = change >= 0

    # Bubble size: sqrt scaling so large caps don't dwarf small ones
    # Min size 8, max size ~32
    size = 8
    if ticker.market_cap and max_cap:
        size = 8 + math.sqrt(ticker.market_cap / max_cap) * 24
        size = round(size, 1)

    # Color based on performance
    color = "#EAF3DE" if is_up else "#FCEBEB"
    border_color = "#3B6D11" if is_up else "#A32D2D"

    return {
        "symbol":       ticker.symbol,
        "name":         ticker.name,
        "market":       ticker.market.value,
        "x":            rank,               # Cap rank on X axis
        "y":            round(change, 2),   # % change on Y axis
        "size":         size,               # Bubble radius
        "color":        color,              # Fill color
        "border_color": border_color,
        "price":        ticker.price,
        "change_pct":   round(change, 2),
        "market_cap":   ticker.market_cap,
        "is_live":      ticker.is_live,
        "source":       ticker.source.value,
    }


# ── INTERNAL HELPERS ──────────────────────────────────────

def _safe_float(value) -> Optional[float]:
    """
    Safely convert a value to float.
    Returns None if value is None, NaN, or infinite.
    These would break JSON serialization.
    """
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None
