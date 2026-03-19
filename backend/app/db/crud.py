# =============================================================
# backend/app/db/crud.py
# PURPOSE:  All database read/write operations (CRUD)
#           Replaces every _demo_*_store dict in the API files
#
# PATTERN:
#   Every function takes a db: AsyncSession argument
#   Injected via FastAPI Depends(get_db)
#   No raw SQL — uses SQLAlchemy ORM throughout
#
# LAST UPDATED: March 2026
# =============================================================

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import List, Optional
from uuid import UUID
import uuid

from app.db.models import Holding, Watchlist, Alert, AlertLog, UserPreference


# ── HOLDINGS ──────────────────────────────────────────────

async def get_holdings(db: AsyncSession, user_id: str) -> List[Holding]:
    """Get all holdings for a user"""
    result = await db.execute(
        select(Holding)
        .where(Holding.user_id == UUID(user_id))
        .order_by(Holding.created_at)
    )
    return result.scalars().all()


async def upsert_holding(
    db: AsyncSession,
    user_id: str,
    symbol: str,
    market: str,
    quantity: float,
    avg_cost: float,
    currency: str = "USD",
    notes: Optional[str] = None,
) -> Holding:
    """
    Insert or update a holding.
    If symbol already exists for user, updates quantity and avg_cost.
    Uses PostgreSQL UPSERT (ON CONFLICT DO UPDATE).
    """
    stmt = pg_insert(Holding).values(
        id=uuid.uuid4(),
        user_id=UUID(user_id),
        symbol=symbol.upper(),
        market=market,
        quantity=quantity,
        avg_cost=avg_cost,
        currency=currency,
        notes=notes,
    ).on_conflict_do_update(
        constraint="holdings_user_symbol_unique",
        set_={
            "quantity": quantity,
            "avg_cost": avg_cost,
            "currency": currency,
            "notes":    notes,
        }
    ).returning(Holding)

    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def delete_holding(db: AsyncSession, user_id: str, symbol: str) -> bool:
    """Delete a holding. Returns True if deleted, False if not found."""
    result = await db.execute(
        delete(Holding)
        .where(and_(
            Holding.user_id == UUID(user_id),
            Holding.symbol  == symbol.upper()
        ))
    )
    await db.commit()
    return result.rowcount > 0


# ── WATCHLISTS ────────────────────────────────────────────

async def get_watchlist(db: AsyncSession, user_id: str) -> List[Watchlist]:
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == UUID(user_id))
    )
    return result.scalars().all()


async def add_to_watchlist(
    db: AsyncSession,
    user_id: str,
    symbol: str,
    market: str,
) -> Watchlist:
    stmt = pg_insert(Watchlist).values(
        id=uuid.uuid4(),
        user_id=UUID(user_id),
        symbol=symbol.upper(),
        market=market,
    ).on_conflict_do_nothing(
        constraint="watchlists_user_symbol_unique"
    ).returning(Watchlist)

    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()


async def remove_from_watchlist(
    db: AsyncSession,
    user_id: str,
    symbol: str,
) -> bool:
    result = await db.execute(
        delete(Watchlist).where(and_(
            Watchlist.user_id == UUID(user_id),
            Watchlist.symbol  == symbol.upper()
        ))
    )
    await db.commit()
    return result.rowcount > 0


# ── ALERTS ────────────────────────────────────────────────

async def get_alerts(db: AsyncSession, user_id: str) -> List[Alert]:
    """Get all active alerts for a user"""
    result = await db.execute(
        select(Alert).where(and_(
            Alert.user_id  == UUID(user_id),
            Alert.is_active == True
        )).order_by(Alert.created_at.desc())
    )
    return result.scalars().all()


async def create_alert(
    db: AsyncSession,
    user_id: str,
    symbol: str,
    market: str,
    condition: str,
    price: float,
) -> Alert:
    alert = Alert(
        user_id=UUID(user_id),
        symbol=symbol.upper(),
        market=market,
        condition=condition,
        price=price,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def deactivate_alert(
    db: AsyncSession,
    user_id: str,
    alert_id: str,
) -> bool:
    """Soft delete — marks is_active=False"""
    result = await db.execute(
        update(Alert)
        .where(and_(
            Alert.id      == UUID(alert_id),
            Alert.user_id == UUID(user_id)
        ))
        .values(is_active=False)
    )
    await db.commit()
    return result.rowcount > 0


async def get_active_alerts_for_symbol(
    db: AsyncSession,
    symbol: str,
) -> List[Alert]:
    """Used by WebSocket price checker to find alerts to trigger"""
    result = await db.execute(
        select(Alert).where(and_(
            Alert.symbol   == symbol.upper(),
            Alert.is_active == True
        ))
    )
    return result.scalars().all()


async def mark_alert_triggered(
    db: AsyncSession,
    alert_id: str,
    price_at_trigger: float,
    notification_channel: str = "telegram",
) -> None:
    """Record alert trigger + log it"""
    # Update alert (deactivate so it doesn't fire again)
    await db.execute(
        update(Alert)
        .where(Alert.id == UUID(alert_id))
        .values(
            is_active=False,
            last_triggered=func.now(),
            triggered_count=Alert.triggered_count + 1,
        )
    )
    # Log the trigger event
    log = AlertLog(
        alert_id=UUID(alert_id),
        price_at_trigger=price_at_trigger,
        notification_sent=True,
        notification_channel=notification_channel,
    )
    db.add(log)
    await db.commit()


# ── USER PREFERENCES ──────────────────────────────────────

async def get_preferences(
    db: AsyncSession,
    user_id: str,
) -> UserPreference:
    """Get user preferences, creating defaults if not found"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == UUID(user_id))
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Create defaults
        prefs = UserPreference(user_id=UUID(user_id))
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)

    return prefs


async def update_preferences(
    db: AsyncSession,
    user_id: str,
    **kwargs,
) -> UserPreference:
    await db.execute(
        update(UserPreference)
        .where(UserPreference.user_id == UUID(user_id))
        .values(**kwargs)
    )
    await db.commit()
    return await get_preferences(db, user_id)


# Import here to avoid circular import in mark_alert_triggered
from sqlalchemy.sql import func
