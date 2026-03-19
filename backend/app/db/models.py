# =============================================================
# backend/app/db/models.py
# PURPOSE:  SQLAlchemy ORM models — maps Python classes to DB tables
#
# TABLES:
#   Holding          → user portfolio positions
#   Watchlist        → user watchlist symbols
#   Alert            → price/volume alert rules
#   AlertLog         → history of triggered alerts
#   UserPreference   → per-user dashboard settings
#
# MATCHES: backend/app/db/migrations/001_initial_schema.sql
#
# LAST UPDATED: March 2026
# =============================================================

from sqlalchemy import (
    Column, String, Float, Boolean, Integer,
    DateTime, Text, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Holding(Base):
    __tablename__ = "holdings"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), nullable=False, index=True)
    symbol     = Column(String(20), nullable=False)
    market     = Column(String(10), nullable=False)   # crypto|india|us
    quantity   = Column(Float, nullable=False)
    avg_cost   = Column(Float, nullable=False)
    currency   = Column(String(3), nullable=False, default="USD")
    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="holdings_user_symbol_unique"),
        CheckConstraint("quantity > 0",  name="holdings_quantity_positive"),
        CheckConstraint("avg_cost > 0",  name="holdings_avg_cost_positive"),
        CheckConstraint("market IN ('crypto','india','us')", name="holdings_market_valid"),
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id  = Column(UUID(as_uuid=True), nullable=False, index=True)
    symbol   = Column(String(20), nullable=False)
    market   = Column(String(10), nullable=False)
    name     = Column(String(50), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="watchlists_user_symbol_unique"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), nullable=False, index=True)
    symbol           = Column(String(20), nullable=False)
    market           = Column(String(10), nullable=False)
    condition        = Column(String(10), nullable=False)   # above|below
    price            = Column(Float, nullable=False)
    is_active        = Column(Boolean, nullable=False, default=True)
    notify_telegram  = Column(Boolean, default=True)
    notify_email     = Column(Boolean, default=False)
    triggered_count  = Column(Integer, default=0)
    last_triggered   = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("condition IN ('above','below')", name="alerts_condition_valid"),
    )


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id             = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"))
    user_id              = Column(UUID(as_uuid=True), nullable=False)
    symbol               = Column(String(20), nullable=False)
    triggered_at         = Column(DateTime(timezone=True), server_default=func.now())
    price_at_trigger     = Column(Float, nullable=False)
    notification_sent    = Column(Boolean, default=False)
    notification_channel = Column(String(20), nullable=True)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id           = Column(UUID(as_uuid=True), primary_key=True)
    default_index     = Column(String(20), default="all")
    default_timeframe = Column(String(5),  default="1d")
    default_theme     = Column(String(10), default="system")
    currency_display  = Column(String(3),  default="USD")
    show_ai_insights  = Column(Boolean, default=True)
    show_portfolio    = Column(Boolean, default=True)
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
