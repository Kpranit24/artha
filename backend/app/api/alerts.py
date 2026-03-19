# =============================================================
# backend/app/api/alerts.py
# PURPOSE:  Price alerts — wired to real Postgres
# LAST UPDATED: March 2026
# =============================================================

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.crud import (
    get_alerts, create_alert, deactivate_alert,
    get_active_alerts_for_symbol, mark_alert_triggered,
)

router = APIRouter()


class AlertInput(BaseModel):
    symbol:    str
    market:    str
    condition: str   # "above" | "below"
    price:     float


@router.post("/alerts")
async def create_alert_route(
    alert: AlertInput,
    user: dict = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    if alert.condition not in ["above", "below"]:
        raise HTTPException(status_code=400, detail="Condition must be 'above' or 'below'")
    if alert.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")

    new_alert = await create_alert(
        db, user["id"], alert.symbol, alert.market, alert.condition, alert.price
    )
    return JSONResponse({
        "success": True,
        "data": {"id": str(new_alert.id), "message": f"Alert created for {alert.symbol.upper()}"},
    })


@router.get("/alerts")
async def get_alerts_route(
    user: dict = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    alerts = await get_alerts(db, user["id"])
    return JSONResponse({
        "success": True,
        "data": {
            "alerts": [
                {"id": str(a.id), "symbol": a.symbol, "market": a.market,
                 "condition": a.condition, "price": a.price,
                 "created_at": a.created_at.isoformat()}
                for a in alerts
            ],
            "total": len(alerts),
        },
    })


@router.delete("/alerts/{alert_id}")
async def delete_alert_route(
    alert_id: str,
    user: dict = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    deleted = await deactivate_alert(db, user["id"], alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
    return JSONResponse({"success": True, "message": "Alert deleted"})


# ── ALERT CHECKER (called from WebSocket loop) ─────────────

async def check_alerts_for_symbol(
    symbol: str,
    current_price: float,
    db: AsyncSession,
):
    """Check and fire alerts when price crosses threshold"""
    alerts = await get_active_alerts_for_symbol(db, symbol)
    for alert in alerts:
        triggered = (
            (alert.condition == "above" and current_price >= alert.price) or
            (alert.condition == "below" and current_price <= alert.price)
        )
        if triggered:
            await _send_notification(alert, current_price)
            await mark_alert_triggered(db, str(alert.id), current_price)


async def _send_notification(alert, price: float):
    from app.agents.monitors.supervisor import send_alert
    curr = "₹" if alert.market == "india" else "$"
    direction = "▲" if alert.condition == "above" else "▼"
    msg = (
        f"Price alert triggered: {alert.symbol}\n"
        f"{direction} {curr}{price:,.2f} "
        f"({alert.condition} your target {curr}{alert.price:,.2f})"
    )
    await send_alert("YELLOW", msg, auto_fixed=False)
