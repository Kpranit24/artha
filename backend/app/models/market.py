# =============================================================
# backend/app/models/market.py
# PURPOSE:  Standard data shapes for ALL market data
#           Every API response gets normalized to these types
#           before touching the frontend
#
# RULE:     Never let raw API responses reach the frontend.
#           Always normalize through these types first.
#           This means if CoinGecko changes their API,
#           we only fix it in ONE place (data/coingecko.py)
#           not everywhere.
#
# ADDING A NEW FIELD:
#   1. Add here with Optional type and None default
#   2. Update normalize.py to populate it
#   3. Update frontend/types/market.ts to match
#   4. Add a comment explaining what it is
#
# AI AGENT NOTE:
#   If insight_agent output shape changes, update InsightData here
#   If TickerData changes, backend_agent will alert on type errors
#
# LAST UPDATED: March 2026
# =============================================================

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── ENUMS ─────────────────────────────────────────────────

class Market(str, Enum):
    """Which market this ticker belongs to"""
    INDIA = "india"     # NSE/BSE listed
    US = "us"           # NYSE/NASDAQ listed
    CRYPTO = "crypto"   # Crypto exchanges


class Currency(str, Enum):
    """
    Always explicit — never assume INR or USD.
    India tickers: INR
    US tickers: USD
    Crypto: USD (always, for comparability)
    """
    INR = "INR"
    USD = "USD"


class DataSource(str, Enum):
    """
    Which data source provided this data.
    Used for showing 'delayed' badge and debugging.
    """
    COINGECKO = "coingecko"
    YAHOO = "yahoo"
    YFINANCE = "yfinance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    TWELVE_DATA = "twelve_data"
    STATIC_DEMO = "static_demo"   # Fallback hardcoded data


class Timeframe(str, Enum):
    """
    Supported chart timeframes.
    All chart components use this — changing here
    updates the entire app.
    """
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    YTD = "ytd"
    FIVE_YEAR = "5y"


# ── CORE TICKER DATA ──────────────────────────────────────

class TickerData(BaseModel):
    """
    Standard shape for ALL market data across the app.
    CoinGecko, Yahoo Finance, NSE, yfinance all get
    normalized into this before being used anywhere.

    FRONTEND MATCH: frontend/types/market.ts → TickerData
    Keep these in sync when adding fields.
    """

    # Identity
    symbol: str             # "TCS.NS", "BTC", "AAPL" — always uppercase
    name: str               # "Tata Consultancy Services", "Bitcoin"
    market: Market          # india | us | crypto
    currency: Currency      # Always explicit

    # Price data
    price: float            # Current price
    price_open: Optional[float] = None
    price_high: Optional[float] = None
    price_low: Optional[float] = None
    price_close: Optional[float] = None

    # Change data
    change_1d: Optional[float] = None   # % change — 1.4 means +1.4%
    change_7d: Optional[float] = None
    change_30d: Optional[float] = None
    change_ytd: Optional[float] = None

    # Volume and market cap
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None  # Always in USD for comparability

    # Fundamentals (India/US equities only)
    # FUTURE: Populated by fundamentals agent (not built yet)
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    revenue_growth: Optional[float] = None

    # 7-day sparkline prices (for mini charts)
    sparkline: Optional[List[float]] = None

    # ATH (all time high)
    ath: Optional[float] = None
    ath_change_pct: Optional[float] = None

    # Metadata
    source: DataSource              # Which API provided this
    is_live: bool = True            # False if from cache/static
    fetched_at: datetime            # When this was fetched
    delayed_by_seconds: int = 0    # How old is this data

    @property
    def is_delayed(self) -> bool:
        """True if data is more than 60 seconds old"""
        age = (datetime.utcnow() - self.fetched_at).total_seconds()
        return age > 60

    @property
    def display_price(self) -> str:
        """Formatted price string for display"""
        if self.currency == Currency.INR:
            return f"₹{self.price:,.2f}"
        return f"${self.price:,.2f}"


# ── OHLCV DATA (for candlestick charts) ───────────────────

class OHLCVPoint(BaseModel):
    """Single candlestick data point"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVData(BaseModel):
    """Full OHLCV series for a ticker"""
    symbol: str
    timeframe: Timeframe
    candles: List[OHLCVPoint]
    source: DataSource
    fetched_at: datetime


# ── HEATMAP DATA ──────────────────────────────────────────

class HeatmapBubble(BaseModel):
    """
    One bubble in the heatmap chart.
    x = market cap rank (1 = largest)
    y = % change (positive = up, negative = down)
    size = relative market cap (for bubble size)
    """
    symbol: str
    name: str
    market: Market
    x: float        # Market cap rank
    y: float        # % change
    size: float     # Bubble radius (computed from market cap)
    color: str      # Hex color based on performance
    price: float
    change_pct: float
    market_cap: Optional[float] = None
    sector: Optional[str] = None


class HeatmapData(BaseModel):
    """Full heatmap dataset"""
    bubbles: List[HeatmapBubble]
    timeframe: Timeframe
    index: str          # "nifty50", "nasdaq100", "crypto_top20"
    fetched_at: datetime
    is_live: bool


# ── AI INSIGHT DATA ───────────────────────────────────────

class InsightData(BaseModel):
    """
    AI-generated market insight from insight_agent.
    Generated by Claude API — cached for CACHE_TTL_INSIGHTS seconds
    to control costs.

    COST: ~$0.003 per insight at claude-sonnet pricing
    CACHE: 1 hour — same ticker rarely needs fresh analysis every minute
    """
    symbol: str
    headline: str           # "TCS up 2.3% on Q4 beat" (1 sentence)
    summary: str            # 2-3 sentence analysis
    bull_case: str          # Why it might go up
    bear_case: str          # Why it might go down
    key_drivers: List[str]  # Top 3 reasons for current movement
    sentiment: str          # "bullish" | "bearish" | "neutral"
    confidence: str         # "high" | "medium" | "low"
    disclaimer: str = "Not financial advice. For informational purposes only."
    generated_at: datetime
    model_used: str         # Which Claude model generated this


# ── PORTFOLIO DATA ────────────────────────────────────────

class Holding(BaseModel):
    """Single holding in a user's portfolio"""
    symbol: str
    name: str
    market: Market
    quantity: float
    avg_cost: float         # Average cost basis
    currency: Currency
    live_price: Optional[float] = None   # Populated from TickerData
    is_live: bool = False


class PortfolioData(BaseModel):
    """User's complete portfolio with live P&L"""
    holdings: List[Holding]
    total_value: float
    total_invested: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    currency: Currency = Currency.USD   # All values normalized to USD
    last_updated: datetime


# ── API RESPONSE WRAPPER ──────────────────────────────────

class APIResponse(BaseModel):
    """
    Standard wrapper for all API responses.
    Every endpoint returns this shape — consistent for frontend.
    """
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    disclaimer: str = "Not financial advice. All data for informational purposes only."
    timestamp: datetime = datetime.utcnow()
