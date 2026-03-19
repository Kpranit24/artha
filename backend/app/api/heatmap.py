# =============================================================
# backend/app/api/heatmap.py
# PURPOSE:  /api/heatmap endpoint — serves bubble chart data
#
# ENDPOINT:
#   GET /api/heatmap
#   Query params:
#     index     = "all" | "nifty50" | "nasdaq" | "crypto" (default: "all")
#     timeframe = "1d" | "1w" | "1m" | "ytd"             (default: "1d")
#
# RESPONSE:
#   {
#     success:  true,
#     data: {
#       bubbles:     [{symbol, x, y, size, color, ...}],
#       top_movers:  {gainers: [...], losers: [...]},
#       market_insight: {...},
#       is_live:     true,
#       fetched_at:  "2026-03-19T...",
#     },
#     disclaimer: "Not financial advice..."
#   }
#
# CACHING:
#   15 seconds (handled in data_agent.py via Redis)
#   1000 concurrent users → ~4 CoinGecko calls/min (well within free limit)
#
# RATE LIMITS:
#   Free tier:  10 req/min per IP
#   Pro tier:   100 req/min
#
# AI AGENT MONITORS:
#   backend_agent → alerts if avg response > 500ms
#
# LAST UPDATED: March 2026
# =============================================================

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.agents.data_agent import run_heatmap_workflow
from app.models.market import Timeframe
from app.api.deps import get_current_user_optional, check_rate_limit


router = APIRouter()


@router.get("/heatmap")
async def get_heatmap(
    index: str = Query(
        default="all",
        description="Index to show: all | nifty50 | nifty_it | nifty_bank | nasdaq | sp500 | crypto"
    ),
    timeframe: str = Query(
        default="1d",
        description="Timeframe: 1d | 1w | 1m | 3m | 6m | 1y | ytd"
    ),
    # Optional auth — free users get less frequent refresh
    user=Depends(get_current_user_optional),
    # Rate limiting — enforced based on user tier
    _=Depends(check_rate_limit),
):
    """
    Returns bubble heatmap data for the Plotly Scattergl chart.

    X-axis = market cap rank (1 = largest)
    Y-axis = % change for the selected timeframe
    Bubble size = relative market cap
    Color = green (up) or red (down)

    Data is cached 15 seconds — safe to poll frequently.
    """

    # Validate timeframe
    try:
        tf = Timeframe(timeframe)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe '{timeframe}'. Use: 1d, 1w, 1m, 3m, 6m, 1y, ytd"
        )

    # Validate index
    valid_indices = ["all", "nifty50", "nifty_it", "nifty_bank", "nasdaq", "sp500", "crypto", "crypto_top20"]
    if index not in valid_indices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid index '{index}'. Use: {', '.join(valid_indices)}"
        )

    # Run the 4-agent workflow (cached in Redis)
    data = await run_heatmap_workflow(index=index, timeframe=tf)

    return JSONResponse({
        "success": True,
        "data":    data,
        "disclaimer": "Not financial advice. All data for informational purposes only.",
    })
