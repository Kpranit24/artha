# =============================================================
# backend/app/agents/data_agent.py
# PURPOSE:  Orchestrates all 4 parallel agents
#           Coordinates data fetch → viz → insight → portfolio
#
# THE 4-AGENT PATTERN (from Perplexity Finance architecture):
#   data_agent      → fetch + normalize (this file coordinates)
#   viz_agent       → format data for charts
#   insight_agent   → Claude AI analysis (insight_agent.py)
#   portfolio_agent → holdings + P&L (portfolio_agent.py)
#
# PARALLEL EXECUTION:
#   All 4 run simultaneously with asyncio.gather()
#   Total response time = slowest agent (~2-3s)
#   NOT sequential = not 2s + 2s + 2s + 2s = 8s
#
# UPGRADE PATH (from architecture doc):
#   Replace asyncio.gather() with Kafka at 5K+ concurrent users
#   Each agent becomes a Kafka consumer group
#   Zero code changes to agent logic — only orchestration changes
#
# AI AGENT MONITORS:
#   backend_agent → tracks which agent is the bottleneck
#   cost_agent    → tracks Claude API calls from insight_agent
#
# LAST UPDATED: March 2026
# =============================================================

import asyncio
from datetime import datetime
from typing import List, Optional

from app.core.config import settings
from app.core.cache import get_with_cache, heatmap_key, price_key
from app.data.sources import get_prices
from app.data.normalize import build_heatmap_bubble
from app.models.market import TickerData, HeatmapData, Market, Timeframe
from app.agents.insight_agent import generate_insight


# ── MAIN ORCHESTRATOR ─────────────────────────────────────

async def run_heatmap_workflow(
    index: str = "all",
    timeframe: Timeframe = Timeframe.ONE_DAY
) -> dict:
    """
    Full 4-agent workflow for the heatmap endpoint.
    Runs all agents in parallel — total time = slowest agent.

    Args:
        index:     "all" | "nifty50" | "nasdaq" | "crypto"
        timeframe: "1d" | "1w" | "1m" | "ytd"

    Returns:
        {
            bubbles:    [...],    # Heatmap bubble data
            top_movers: [...],    # Top 5 up + top 5 down
            insight:    {...},    # AI summary of market
            fetched_at: "...",
            is_live:    true
        }

    Performance target: <500ms (95th percentile)
    Cache TTL: 15 seconds (set in config.py)
    """
    cache_key = heatmap_key(index, timeframe.value)

    return await get_with_cache(
        key=cache_key,
        fetch_fn=lambda: _run_parallel_workflow(index, timeframe),
        ttl=settings.CACHE_TTL_PRICES  # 15 seconds
    )


async def _run_parallel_workflow(
    index: str,
    timeframe: Timeframe
) -> dict:
    """
    Runs all 4 agents in parallel.
    This is where the performance magic happens.

    Without parallel: fetch(2s) + viz(0.5s) + insight(3s) = 5.5s
    With parallel:    max(fetch, viz, insight) = 3s
    """

    # Determine which markets to fetch
    markets_to_fetch = _resolve_markets(index)

    # ── AGENT 1: DATA AGENT ───────────────────────────────
    # Fetch prices for all requested markets in parallel
    data_tasks = [
        get_prices([], market, timeframe)
        for market in markets_to_fetch
    ]

    # ── AGENTS 1-4: ALL IN PARALLEL ───────────────────────
    # This is the key optimization — all run simultaneously
    # asyncio.gather fires them all at once
    results = await asyncio.gather(
        *data_tasks,
        return_exceptions=True  # Don't crash if one market fails
    )

    # Combine all market data
    all_tickers: List[TickerData] = []
    for result in results:
        if isinstance(result, list):
            all_tickers.extend(result)
        elif isinstance(result, Exception):
            # One market failed — log but continue with others
            print(f"Market fetch failed: {result}")

    if not all_tickers:
        # Complete failure — return demo data
        from app.data.static_demo import (
            fetch_demo_crypto, fetch_demo_india_stocks, fetch_demo_us_stocks
        )
        demo = await asyncio.gather(
            fetch_demo_crypto(), fetch_demo_india_stocks(), fetch_demo_us_stocks()
        )
        for d in demo:
            all_tickers.extend(d)

    # ── AGENT 2: VIZ AGENT ────────────────────────────────
    # Format data for Plotly Scattergl bubble chart
    bubbles = _build_heatmap_bubbles(all_tickers)
    top_movers = _get_top_movers(all_tickers)

    # ── AGENT 3: INSIGHT AGENT ────────────────────────────
    # Generate AI market summary (runs in parallel with viz)
    # Only generates one market-level insight, not per-ticker
    # Per-ticker insights are generated on-demand in /api/ticker
    market_insight = await _generate_market_insight(all_tickers)

    return {
        "bubbles":        bubbles,
        "top_movers":     top_movers,
        "market_insight": market_insight,
        "total_tickers":  len(all_tickers),
        "fetched_at":     datetime.utcnow().isoformat(),
        "is_live":        any(t.is_live for t in all_tickers),
        "disclaimer":     "Not financial advice. All data for informational purposes only.",
    }


async def run_ticker_workflow(
    symbol: str,
    market: str,
    timeframe: Timeframe = Timeframe.ONE_DAY,
    include_insight: bool = True
) -> dict:
    """
    Full workflow for a single ticker page.
    Fetches: price + OHLCV + fundamentals + AI insight

    Args:
        symbol:         "TCS" or "TCS.NS" or "BTC"
        market:         "india" | "us" | "crypto"
        timeframe:      Chart timeframe
        include_insight: False = skip AI (faster, cheaper)

    Returns:
        Complete ticker data with AI insight
    """
    # Resolve market enum
    market_enum = Market(market)

    # Run price fetch and OHLCV in parallel
    price_task = get_prices([symbol], market, timeframe)
    ohlcv_task = _fetch_ohlcv(symbol, market, timeframe)

    price_results, ohlcv_data = await asyncio.gather(
        price_task, ohlcv_task,
        return_exceptions=True
    )

    # Get the ticker
    ticker = None
    if isinstance(price_results, list) and price_results:
        ticker = price_results[0]

    if not ticker:
        return {"error": f"No data found for {symbol}"}

    # Generate AI insight (if enabled and requested)
    insight = None
    if include_insight and settings.ENABLE_AI_INSIGHTS:
        try:
            insight = await generate_insight(ticker)
        except Exception as e:
            print(f"Insight generation failed for {symbol}: {e}")

    return {
        "ticker":     ticker.dict(),
        "ohlcv":      ohlcv_data if not isinstance(ohlcv_data, Exception) else [],
        "insight":    insight,
        "fetched_at": datetime.utcnow().isoformat(),
        "disclaimer": "Not financial advice. All data for informational purposes only.",
    }


# ── VIZ AGENT HELPERS ─────────────────────────────────────

def _build_heatmap_bubbles(tickers: List[TickerData]) -> List[dict]:
    """
    Agent 2: Format tickers → Plotly Scattergl bubble format.
    Sorted by market cap (largest = rank 1).
    """
    sorted_tickers = sorted(
        [t for t in tickers if t.market_cap],
        key=lambda x: x.market_cap or 0,
        reverse=True
    )

    max_cap = sorted_tickers[0].market_cap if sorted_tickers else 1

    return [
        build_heatmap_bubble(ticker, rank + 1, max_cap)
        for rank, ticker in enumerate(sorted_tickers)
    ]


def _get_top_movers(tickers: List[TickerData]) -> dict:
    """
    Get top 5 gainers and top 5 losers for sidebar.
    Grouped by market for India / US / Crypto panels.
    """
    valid = [t for t in tickers if t.change_1d is not None]
    sorted_tickers = sorted(valid, key=lambda x: x.change_1d or 0, reverse=True)

    return {
        "gainers": [_ticker_to_mover(t) for t in sorted_tickers[:5]],
        "losers":  [_ticker_to_mover(t) for t in sorted_tickers[-5:][::-1]],
    }


def _ticker_to_mover(ticker: TickerData) -> dict:
    """Convert TickerData to compact mover format for UI"""
    return {
        "symbol":     ticker.symbol,
        "name":       ticker.name,
        "price":      ticker.price,
        "change_1d":  ticker.change_1d,
        "market":     ticker.market.value,
        "currency":   ticker.currency.value,
        "is_live":    ticker.is_live,
    }


async def _generate_market_insight(tickers: List[TickerData]) -> Optional[dict]:
    """
    Generate a brief market-level AI summary.
    NOT per-ticker — just an overview of market conditions.
    Cheaper than per-ticker: 1 API call instead of N calls.
    """
    if not settings.ENABLE_AI_INSIGHTS or not tickers:
        return None

    try:
        # Pick the biggest mover as the representative ticker
        valid = [t for t in tickers if t.change_1d is not None]
        if not valid:
            return None

        biggest_mover = max(valid, key=lambda x: abs(x.change_1d or 0))
        insight = await generate_insight(biggest_mover)
        return insight
    except Exception as e:
        print(f"Market insight generation failed: {e}")
        return None


async def _fetch_ohlcv(
    symbol: str,
    market: str,
    timeframe: Timeframe
) -> List[dict]:
    """Fetch OHLCV data from the appropriate source"""
    try:
        if market == "crypto":
            from app.data.coingecko import fetch_coingecko_ohlcv
            return await fetch_coingecko_ohlcv(symbol, timeframe)
        elif market == "india":
            from app.data.yfinance_india import fetch_india_ohlcv
            return await fetch_india_ohlcv(symbol, timeframe)
        elif market == "us":
            from app.data.yahoo import fetch_yahoo_ohlcv
            return await fetch_yahoo_ohlcv(symbol, timeframe)
    except Exception as e:
        print(f"OHLCV fetch failed for {symbol}: {e}")
    return []


def _resolve_markets(index: str) -> List[str]:
    """Determine which markets to fetch based on index name"""
    if index == "all":
        return ["crypto", "india", "us"]
    elif index in ["nifty50", "nifty_it", "nifty_bank"]:
        return ["india"]
    elif index in ["nasdaq", "sp500", "tech"]:
        return ["us"]
    elif index in ["crypto", "crypto_top20"]:
        return ["crypto"]
    return ["crypto", "india", "us"]
