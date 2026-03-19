# =============================================================
# backend/app/api/ticker.py
# PURPOSE:  /api/ticker/{symbol} endpoint
#           Returns full data for a single stock/crypto
#
# ENDPOINT:
#   GET /api/ticker/{symbol}
#   Path params:
#     symbol = "TCS" | "BTC" | "AAPL"
#   Query params:
#     market    = "india" | "us" | "crypto"
#     timeframe = "1d" | "1w" | "1m" | "1y"
#     insight   = true | false (default: true)
#
# RESPONSE:
#   {
#     ticker:  { price, change, volume, pe_ratio, ... },
#     ohlcv:   [ { timestamp, open, high, low, close, volume }, ... ],
#     insight: { headline, summary, bull_case, bear_case, ... },
#   }
#
# CACHING:
#   Price data:  15s TTL (Redis L1)
#   OHLCV data:  5min TTL (Redis L2)
#   AI insight:  1hr TTL (expensive to generate)
#
# AI AGENT MONITORS:
#   backend_agent → response time target < 3s (insight adds 2-3s)
#   cost_agent    → insight calls vs daily Claude budget
#
# LAST UPDATED: March 2026
# =============================================================

from fastapi import APIRouter, Path, Query, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.agents.data_agent import run_ticker_workflow
from app.models.market import Timeframe
from app.api.deps import get_current_user_optional, check_rate_limit


router = APIRouter()

# Valid markets
VALID_MARKETS = ["india", "us", "crypto"]


@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str = Path(
        description="Ticker symbol: TCS | INFY | BTC | AAPL | NVDA"
    ),
    market: str = Query(
        default="crypto",
        description="Market: india | us | crypto"
    ),
    timeframe: str = Query(
        default="1m",
        description="Chart timeframe: 1d | 1w | 1m | 3m | 6m | 1y | ytd"
    ),
    insight: bool = Query(
        default=True,
        description="Include AI insight (slower, set false for faster response)"
    ),
    user=Depends(get_current_user_optional),
    _=Depends(check_rate_limit),
):
    """
    Returns complete data for a single ticker.
    Includes: live price, OHLCV chart data, AI insight.

    Performance note:
        Without insight: ~200ms
        With insight:    ~2-3s first time, ~50ms when cached (1hr)
    """

    # Validate market
    if market not in VALID_MARKETS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid market '{market}'. Use: {', '.join(VALID_MARKETS)}"
        )

    # Validate timeframe
    try:
        tf = Timeframe(timeframe)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe '{timeframe}'. Use: 1d, 1w, 1m, 3m, 6m, 1y, ytd"
        )

    # Free users don't get AI insights to manage costs
    # Pro/VIP users get full insight
    user_tier = user.get("tier", "free") if user else "free"
    include_insight = insight and (user_tier in ["pro", "vip"] or True)
    # NOTE: Currently allowing all users — remove "or True" to restrict

    data = await run_ticker_workflow(
        symbol=symbol.upper(),
        market=market,
        timeframe=tf,
        include_insight=include_insight,
    )

    if "error" in data:
        raise HTTPException(
            status_code=404,
            detail=data["error"]
        )

    return JSONResponse({
        "success":    True,
        "data":       data,
        "disclaimer": "Not financial advice. All data for informational purposes only.",
    })
