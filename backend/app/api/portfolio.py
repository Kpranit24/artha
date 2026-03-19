# =============================================================
# backend/app/api/portfolio.py
# PURPOSE:  Portfolio endpoints — wired to real Postgres via SQLAlchemy
# LAST UPDATED: March 2026
# =============================================================

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import asyncio

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.crud import (
    get_holdings, upsert_holding, delete_holding,
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    get_preferences, update_preferences,
)
from app.data.sources import get_prices
from app.models.market import Timeframe

router = APIRouter()


class HoldingInput(BaseModel):
    symbol:   str
    market:   str
    quantity: float
    avg_cost: float
    currency: str = "USD"
    notes:    Optional[str] = None


class PreferenceInput(BaseModel):
    default_index:     Optional[str] = None
    default_timeframe: Optional[str] = None
    default_theme:     Optional[str] = None
    show_ai_insights:  Optional[bool] = None


@router.get("/portfolio")
async def get_portfolio(
    user: dict = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    holdings = await get_holdings(db, user["id"])

    if not holdings:
        return JSONResponse({
            "success": True,
            "data": {
                "holdings": [], "total_value": 0, "total_invested": 0,
                "unrealized_pnl": 0, "unrealized_pnl_pct": 0, "allocation": [],
                "message": "No holdings yet. Add your first position.",
            },
            "disclaimer": "Not financial advice.",
        })

    holdings_dicts = [
        {"symbol": h.symbol, "market": h.market, "quantity": h.quantity,
         "avg_cost": h.avg_cost, "currency": h.currency, "notes": h.notes}
        for h in holdings
    ]

    enriched = await _enrich_with_live_prices(holdings_dicts)
    totals   = _calculate_totals(enriched)

    return JSONResponse({
        "success": True,
        "data": {**totals, "holdings": enriched,
                 "last_updated": datetime.utcnow().isoformat()},
        "disclaimer": "Not financial advice. All data for informational purposes only.",
    })


@router.post("/portfolio/holdings")
async def add_holding(
    holding: HoldingInput,
    user: dict = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    if holding.market not in ["india", "us", "crypto"]:
        raise HTTPException(status_code=400, detail="Invalid market")
    if holding.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if holding.avg_cost <= 0:
        raise HTTPException(status_code=400, detail="Cost must be positive")

    await upsert_holding(db, user["id"], holding.symbol, holding.market,
                         holding.quantity, holding.avg_cost, holding.currency, holding.notes)

    return JSONResponse({"success": True, "message": f"Holding {holding.symbol.upper()} saved"})


@router.delete("/portfolio/holdings/{symbol}")
async def remove_holding(
    symbol: str,
    user: dict = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    deleted = await delete_holding(db, user["id"], symbol)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Holding {symbol} not found")
    return JSONResponse({"success": True, "message": f"{symbol.upper()} removed"})


@router.get("/portfolio/watchlist")
async def get_watchlist_route(
    user: dict = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    items = await get_watchlist(db, user["id"])
    return JSONResponse({"success": True,
                         "data": [{"symbol": w.symbol, "market": w.market} for w in items]})


@router.post("/portfolio/watchlist/{symbol}")
async def watchlist_add(symbol: str, market: str,
                         user: dict = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    await add_to_watchlist(db, user["id"], symbol, market)
    return JSONResponse({"success": True})


@router.delete("/portfolio/watchlist/{symbol}")
async def watchlist_remove(symbol: str,
                            user: dict = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    await remove_from_watchlist(db, user["id"], symbol)
    return JSONResponse({"success": True})


@router.get("/portfolio/preferences")
async def get_prefs(user: dict = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    p = await get_preferences(db, user["id"])
    return JSONResponse({"success": True, "data": {
        "default_index": p.default_index, "default_timeframe": p.default_timeframe,
        "default_theme": p.default_theme, "show_ai_insights": p.show_ai_insights,
    }})


@router.put("/portfolio/preferences")
async def update_prefs(prefs: PreferenceInput,
                       user: dict = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    updates = {k: v for k, v in prefs.dict().items() if v is not None}
    await update_preferences(db, user["id"], **updates)
    return JSONResponse({"success": True})


# ── SHARED LOGIC ──────────────────────────────────────────

async def _enrich_with_live_prices(holdings: list) -> list:
    by_market: dict = {"crypto": [], "india": [], "us": []}
    for h in holdings:
        by_market[h["market"]].append(h["symbol"])

    results = await asyncio.gather(
        get_prices(by_market["crypto"], "crypto", Timeframe.ONE_DAY),
        get_prices(by_market["india"],  "india",  Timeframe.ONE_DAY),
        get_prices(by_market["us"],     "us",     Timeframe.ONE_DAY),
        return_exceptions=True
    )

    price_map = {}
    for r in results:
        if isinstance(r, list):
            for t in r:
                price_map[t.symbol.upper()] = {
                    "price": t.price, "change_1d": t.change_1d,
                    "is_live": t.is_live, "source": t.source.value,
                }

    enriched = []
    for h in holdings:
        sym  = h["symbol"].upper()
        live = price_map.get(sym, {})
        ltp  = live.get("price")
        pnl  = (ltp - h["avg_cost"]) * h["quantity"] if ltp else None
        pct  = ((ltp / h["avg_cost"]) - 1) * 100 if ltp and h["avg_cost"] else None
        enriched.append({
            **h,
            "live_price":         ltp,
            "change_1d":          live.get("change_1d"),
            "unrealized_pnl":     round(pnl, 2) if pnl is not None else None,
            "unrealized_pnl_pct": round(pct, 2) if pct is not None else None,
            "current_value":      round(ltp * h["quantity"], 2) if ltp else None,
            "is_live":            live.get("is_live", False),
            "data_source":        live.get("source", "unknown"),
        })
    return enriched


def _calculate_totals(holdings: list) -> dict:
    tv  = sum(h.get("current_value") or 0 for h in holdings)
    ti  = sum(h["avg_cost"] * h["quantity"] for h in holdings)
    pnl = tv - ti
    pct = ((tv / ti) - 1) * 100 if ti else 0
    bm  = {}
    for h in holdings:
        bm[h["market"]] = bm.get(h["market"], 0) + (h.get("current_value") or 0)
    alloc = [{"market": m, "value": round(v, 2),
               "pct": round(v / tv * 100, 1) if tv else 0} for m, v in bm.items()]
    return {"total_value": round(tv, 2), "total_invested": round(ti, 2),
            "unrealized_pnl": round(pnl, 2), "unrealized_pnl_pct": round(pct, 2),
            "allocation": alloc}
