-- =============================================================
-- backend/app/db/migrations/001_initial_schema.sql
-- PURPOSE:  Initial database schema for the finance dashboard
--
-- TABLES:
--   users        → auth (managed by Supabase, just referenced here)
--   holdings     → user portfolio positions
--   watchlists   → user watchlist symbols
--   alerts       → price/volume alert rules
--   alert_logs   → history of triggered alerts
--
-- RUNS:
--   Automatically on first docker-compose up
--   (mounted in docker-compose.yml → initdb.d)
--
-- MANUAL RUN:
--   psql $DATABASE_URL < 001_initial_schema.sql
--
-- UPGRADE PATH:
--   Add TimescaleDB extension for time-series data (market snapshots)
--   Run: CREATE EXTENSION IF NOT EXISTS timescaledb;
--   Then convert market_snapshots to hypertable
--
-- AI AGENT MONITORS:
--   db_agent → checks storage usage, slow queries, backup status
--
-- LAST UPDATED: March 2026
-- =============================================================


-- ── EXTENSION ─────────────────────────────────────────────
-- UUID generation for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ── HOLDINGS ──────────────────────────────────────────────
-- User's portfolio positions
-- One row per symbol per user
-- Updated on add/remove/edit holding

CREATE TABLE IF NOT EXISTS holdings (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL,                -- Supabase auth.users.id
    symbol      VARCHAR(20) NOT NULL,         -- "BTC", "TCS", "AAPL"
    market      VARCHAR(10) NOT NULL,         -- "crypto", "india", "us"
    quantity    DECIMAL(20, 8) NOT NULL,      -- 8 decimal places for crypto
    avg_cost    DECIMAL(20, 2) NOT NULL,      -- Average cost per unit
    currency    VARCHAR(3) NOT NULL DEFAULT 'USD',  -- "USD" or "INR"
    notes       TEXT,                         -- User's personal notes
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One holding per symbol per user
    CONSTRAINT holdings_user_symbol_unique UNIQUE (user_id, symbol),

    -- Validation
    CONSTRAINT holdings_quantity_positive CHECK (quantity > 0),
    CONSTRAINT holdings_avg_cost_positive CHECK (avg_cost > 0),
    CONSTRAINT holdings_market_valid CHECK (market IN ('crypto', 'india', 'us'))
);

-- Index for fast user portfolio lookup
-- Most common query: SELECT * FROM holdings WHERE user_id = $1
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings (user_id);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER holdings_updated_at
    BEFORE UPDATE ON holdings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── WATCHLISTS ────────────────────────────────────────────
-- User's watchlist of symbols to track
-- Separate from holdings — watch without owning

CREATE TABLE IF NOT EXISTS watchlists (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL,
    symbol      VARCHAR(20) NOT NULL,
    market      VARCHAR(10) NOT NULL,
    name        VARCHAR(50),              -- User-given name for the watchlist
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT watchlists_user_symbol_unique UNIQUE (user_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists (user_id);


-- ── ALERTS ────────────────────────────────────────────────
-- Price/volume alert rules
-- Checked every 15 seconds by the backend
-- Triggers notification when condition is met

CREATE TABLE IF NOT EXISTS alerts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL,
    symbol      VARCHAR(20) NOT NULL,
    market      VARCHAR(10) NOT NULL,
    condition   VARCHAR(10) NOT NULL,     -- "above" | "below"
    price       DECIMAL(20, 2) NOT NULL,  -- Target price
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    -- Notification channels
    notify_telegram BOOLEAN DEFAULT TRUE,
    notify_email    BOOLEAN DEFAULT FALSE,
    -- Tracking
    triggered_count INTEGER DEFAULT 0,
    last_triggered  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT alerts_condition_valid CHECK (condition IN ('above', 'below'))
);

-- Fast lookup for alert checker: active alerts for a symbol
CREATE INDEX IF NOT EXISTS idx_alerts_symbol_active
    ON alerts (symbol, is_active)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts (user_id);


-- ── ALERT LOGS ────────────────────────────────────────────
-- History of triggered alerts
-- Used for: audit trail, preventing duplicate alerts

CREATE TABLE IF NOT EXISTS alert_logs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id     UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL,
    symbol       VARCHAR(20) NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    price_at_trigger DECIMAL(20, 2) NOT NULL,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channel VARCHAR(20)   -- "telegram" | "email"
);

-- Fast lookup: "did this alert fire in the last hour?" (prevent duplicates)
CREATE INDEX IF NOT EXISTS idx_alert_logs_alert_id_triggered
    ON alert_logs (alert_id, triggered_at DESC);


-- ── USER PREFERENCES ──────────────────────────────────────
-- User's dashboard preferences
-- Default index, timeframe, theme etc.

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id          UUID PRIMARY KEY,
    default_index    VARCHAR(20) DEFAULT 'all',
    default_timeframe VARCHAR(5) DEFAULT '1d',
    default_theme    VARCHAR(10) DEFAULT 'system',  -- "light" | "dark" | "system"
    currency_display VARCHAR(3) DEFAULT 'USD',
    -- Feature flags per user
    show_ai_insights BOOLEAN DEFAULT TRUE,
    show_portfolio   BOOLEAN DEFAULT TRUE,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ── SAMPLE DATA (development only) ────────────────────────
-- Uncomment for local development
-- DO NOT run in production

-- INSERT INTO holdings (user_id, symbol, market, quantity, avg_cost, currency)
-- VALUES
--     ('00000000-0000-0000-0000-000000000001', 'BTC',  'crypto', 0.5,  62000, 'USD'),
--     ('00000000-0000-0000-0000-000000000001', 'ETH',  'crypto', 3.0,  2800,  'USD'),
--     ('00000000-0000-0000-0000-000000000001', 'INFY', 'india',  50,   1620,  'INR'),
--     ('00000000-0000-0000-0000-000000000001', 'TCS',  'india',  10,   3520,  'INR'),
--     ('00000000-0000-0000-0000-000000000001', 'NVDA', 'us',     5,    620,   'USD')
-- ON CONFLICT (user_id, symbol) DO NOTHING;
