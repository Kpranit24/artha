# =============================================================
# backend/app/core/config.py
# PURPOSE:  Loads all settings from .env file
#           Single source of truth for all configuration
#
# USAGE:
#   from app.core.config import settings
#   print(settings.DATABASE_URL)
#
# HOW IT WORKS:
#   Pydantic reads .env automatically
#   All variables are typed and validated on startup
#   App crashes immediately if a required variable is missing
#   (Better to fail at startup than fail silently at runtime)
#
# ADDING A NEW SETTING:
#   1. Add to .env.example with documentation
#   2. Add field here with type and default
#   3. Use settings.YOUR_FIELD anywhere in the app
#
# LAST UPDATED: March 2026
# =============================================================

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """
    All application settings loaded from .env file.
    Pydantic validates types on startup — wrong types crash immediately.
    Optional fields have defaults and won't crash if missing.
    """

    # ── APP ───────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"

    # ── DATABASE ──────────────────────────────────────────
    # REQUIRED — app won't start without this
    DATABASE_URL: str

    # Supabase-specific (optional — only needed for auth features)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # ── CACHE ─────────────────────────────────────────────
    # REQUIRED — app won't start without this
    REDIS_URL: str = "redis://localhost:6379"

    # Cache TTLs in seconds
    # NOTE: These match Perplexity Finance's refresh rates
    # Change these to reduce API calls if hitting rate limits
    CACHE_TTL_PRICES: int = 15          # Live prices — 15s like Perplexity VIP
    CACHE_TTL_METRICS: int = 300        # Sector data — 5 minutes
    CACHE_TTL_FUNDAMENTALS: int = 3600  # P/E, revenue — 1 hour
    CACHE_TTL_HISTORICAL: int = 86400   # Charts — 24 hours
    CACHE_TTL_INSIGHTS: int = 3600      # AI insights — 1 hour (expensive to generate)

    # ── AI ────────────────────────────────────────────────
    # PRIMARY: Groq (free, fast — 14,400 req/day free tier)
    # Get key: console.groq.com → API Keys
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    # Other good Groq models:
    #   mixtral-8x7b-32768     → fast, good quality
    #   llama-3.1-8b-instant   → fastest, lighter analysis

    # FALLBACK: Claude (paid, best quality)
    # Add later when needed: console.anthropic.com
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 1000

    # Which AI to use — auto-detects based on available keys
    # "groq" | "claude" | "auto" (tries Groq first, falls back to Claude)
    AI_PROVIDER: str = "auto"

    # ── DATA SOURCES — CRYPTO ─────────────────────────────
    COINGECKO_API_KEY: Optional[str] = None  # Empty = free tier (30 req/min)
    USE_COINGECKO_PRO: bool = False

    # ── DATA SOURCES — US STOCKS ──────────────────────────
    USE_YAHOO_FINANCE: bool = True
    ALPHA_VANTAGE_KEY: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    USE_POLYGON: bool = False           # Set true when POLYGON_API_KEY is set

    # ── DATA SOURCES — INDIA ──────────────────────────────
    USE_YFINANCE: bool = True
    TWELVE_DATA_KEY: Optional[str] = None
    USE_TWELVE_DATA: bool = False       # Set true when TWELVE_DATA_KEY is set

    # ── DATA SOURCES — NEWS ───────────────────────────────
    NEWSAPI_KEY: Optional[str] = None
    RSS_FEEDS: str = "https://feeds.finance.yahoo.com/rss/2.0/headline"

    # ── AUTH ──────────────────────────────────────────────
    JWT_SECRET: str = "change-this-in-production"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    @field_validator("JWT_SECRET")
    @classmethod
    def jwt_secret_must_be_changed(cls, v):
        # Warn if still using the default secret in production
        # This is a common security mistake
        if v == "change-this-in-production":
            import warnings
            warnings.warn(
                "JWT_SECRET is using the default value. "
                "Change this in production!",
                UserWarning
            )
        return v

    # ── NOTIFICATIONS ─────────────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_EMAIL: Optional[str] = None

    # ── RATE LIMITING ─────────────────────────────────────
    # Requests per minute by tier
    # Matches Perplexity Finance structure
    RATE_LIMIT_FREE: int = 10
    RATE_LIMIT_PRO: int = 100
    RATE_LIMIT_VIP: int = 1000

    # ── MONITORING ────────────────────────────────────────
    ENABLE_MONITORING: bool = True
    SENTRY_DSN: Optional[str] = None
    DAILY_REPORT_HOUR: int = 9     # 9am IST
    DAILY_REPORT_MINUTE: int = 0

    # Alert thresholds
    ALERT_API_RESPONSE_MS: int = 500
    ALERT_MEMORY_MB: int = 450          # Railway free tier = 512MB
    ALERT_DB_STORAGE_PCT: int = 80
    ALERT_CLAUDE_SPEND_USD: float = 3.0
    DAILY_CLAUDE_BUDGET_USD: float = 5.0

    # ── FEATURE FLAGS ─────────────────────────────────────
    SHOW_DISCLAIMER: bool = True        # Always keep True
    ENABLE_AI_INSIGHTS: bool = True
    ENABLE_PORTFOLIO: bool = True
    ENABLE_ALERTS: bool = True
    DEMO_MODE: bool = False             # Uses static data — no API calls

    class Config:
        # Load from .env file automatically
        env_file = ".env"
        # Allow extra fields without crashing
        # (useful when .env has vars not defined here)
        extra = "ignore"
        case_sensitive = True

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def active_crypto_source(self) -> str:
        """Returns which crypto source is active"""
        if self.USE_COINGECKO_PRO and self.COINGECKO_API_KEY:
            return "coingecko_pro"
        return "coingecko_free"

    @property
    def active_us_source(self) -> str:
        """Returns which US stock source is active"""
        if self.USE_POLYGON and self.POLYGON_API_KEY:
            return "polygon"
        if self.ALPHA_VANTAGE_KEY:
            return "alpha_vantage"
        return "yahoo_finance"

    @property
    def active_india_source(self) -> str:
        """Returns which India stock source is active"""
        if self.USE_TWELVE_DATA and self.TWELVE_DATA_KEY:
            return "twelve_data"
        return "yfinance"


# ── SINGLETON INSTANCE ────────────────────────────────────
# Import this anywhere in the app:
#   from app.core.config import settings
settings = Settings()
