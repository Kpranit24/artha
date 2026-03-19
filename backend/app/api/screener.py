# =============================================================
# backend/app/api/screener.py
# PURPOSE:  /api/screener endpoint — filtered stock/crypto lists
#
# ENDPOINT:
#   GET /api/screener
#   Query params:
#     market    = "all" | "india" | "us" | "crypto"
#     filter    = "gainers" | "losers" | "volume" | "cap" | "ath" | "week"
#     timeframe = "1d" | "1w" | "1m"
#     limit     = 5-50 (default 20)
#
# RESPONSE:
#   { tickers: [TickerData], filter_applied, total }
#
# CACHING:
#   Same underlying data as heatmap (already cached at 15s)
#   Screener just sorts/filters the cached data — very fast
#
# AI AGENT MONITORS:
#   backend_agent → response time should always be < 200ms
#                   (no new API calls, just sorting cached data)
#
# LAST UPDATED: March 2026
# =============================================================

from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse
from typing import List

from app.core.cache import get_with_cache, heatmap_key
from app.data.sources import get_prices
from app.models.market import TickerData, Timeframe
from app.api.deps import get_current_user_optional, check_rate_limit


router = APIRouter()


@router.get("/screener")
async def get_screener(
    market: str = Query(
        default="all",
        description="Market: all | india | us | crypto"
    ),
    filter: str = Query(
        default="gainers",
        description="Sort by: gainers | losers | volume | cap | ath | week"
    ),
    timeframe: str = Query(
        default="1d",
        description="Timeframe for % change: 1d | 1w | 1m"
    ),
    limit: int = Query(
        default=20,
        ge=5,
        le=50,
        description="Number of results (5-50)"
    ),
    user=Depends(get_current_user_optional),
    _=Depends(check_rate_limit),
):
    """
    Returns filtered and sorted list of tickers.
    Uses cached heatmap data — no new API calls.

    Performance: ~50ms (serving from Redis cache)
    """

    try:
        tf = Timeframe(timeframe)
    except ValueError:
        tf = Timeframe.ONE_DAY

    # Determine markets to fetch
    markets = _resolve_markets(market)

    # Get data from cache (or fetch if not cached)
    all_tickers: List[TickerData] = []
    for mkt in markets:
        tickers = await get_prices([], mkt, tf)
        all_tickers.extend(tickers)

    # Apply filter/sort
    sorted_tickers = _apply_filter(all_tickers, filter, tf)

    # Limit results
    results = sorted_tickers[:limit]

    return JSONResponse({
        "success": True,
        "data": {
            "tickers":       [t.dict() for t in results],
            "filter_applied": filter,
            "market":        market,
            "timeframe":     timeframe,
            "total":         len(results),
        },
        "disclaimer": "Not financial advice. All data for informational purposes only.",
    })


def _resolve_markets(market: str) -> List[str]:
    """Convert market string to list of market names"""
    if market == "all":
        return ["crypto", "india", "us"]
    return [market]


def _apply_filter(
    tickers: List[TickerData],
    filter_name: str,
    timeframe: Timeframe
) -> List[TickerData]:
    """
    Sort tickers by the requested filter.
    All filters produce a descending sort (best at top).
    """

    # Remove tickers with None values for the sort key
    def safe_sort(tickers, key_fn, reverse=True):
        valid = [t for t in tickers if key_fn(t) is not None]
        return sorted(valid, key=key_fn, reverse=reverse)

    if filter_name == "gainers":
        # Biggest 24h gainers first
        return safe_sort(tickers, lambda t: t.change_1d or 0)

    elif filter_name == "losers":
        # Biggest 24h losers first (ascending = worst first)
        return safe_sort(tickers, lambda t: t.change_1d or 0, reverse=False)

    elif filter_name == "volume":
        # Highest volume first
        return safe_sort(tickers, lambda t: t.volume_24h or 0)

    elif filter_name == "cap":
        # Largest market cap first
        return safe_sort(tickers, lambda t: t.market_cap or 0)

    elif filter_name == "ath":
        # Closest to all-time high first
        # ath_change_pct is negative (e.g. -5 means 5% below ATH)
        # So closest to ATH = least negative = highest value
        return safe_sort(tickers, lambda t: t.ath_change_pct or -999)

    elif filter_name == "week":
        # Best 7-day performers first
        return safe_sort(tickers, lambda t: t.change_7d or 0)

    # Default: sort by market cap
    return safe_sort(tickers, lambda t: t.market_cap or 0)
