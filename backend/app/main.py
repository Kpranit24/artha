# =============================================================
# backend/app/main.py
# PURPOSE:  FastAPI entry point — full production version
#           All routes, middleware, startup/shutdown
# LAST UPDATED: March 2026
# =============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.core.config import settings
from app.core.database import init_db
from app.core.cache import init_cache, close_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n Starting Artha backend ({settings.ENVIRONMENT})")
    print("  Not financial advice. All data for informational purposes only.\n")

    await init_cache()
    print("  Redis connected")

    await init_db()
    print("  Database connected")

    # Start WebSocket price broadcast loop (background task)
    from app.api.websocket import start_price_broadcast_loop
    asyncio.create_task(start_price_broadcast_loop())
    print("  Price broadcast loop started")

    # Start AI monitoring agents
    if settings.ENABLE_MONITORING:
        from app.agents.monitors.supervisor import start_monitoring
        await start_monitoring()
        print("  AI monitoring agents started")

    print("\n  Backend ready on port 8000\n")
    yield

    await close_cache()
    print("Backend shutdown complete")


# Sentry error tracking (optional)
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        send_default_pii=False,
        traces_sample_rate=0.1,
    )


app = FastAPI(
    title="Artha API",
    description="Free AI-powered market dashboard — India, US, Crypto",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", settings.APP_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── ROUTES ────────────────────────────────────────────────
from app.api import auth, heatmap, ticker, portfolio, screener, alerts, websocket

app.include_router(auth.router,      tags=["auth"])
app.include_router(heatmap.router,   prefix="/api", tags=["heatmap"])
app.include_router(ticker.router,    prefix="/api", tags=["ticker"])
app.include_router(portfolio.router, prefix="/api", tags=["portfolio"])
app.include_router(screener.router,  prefix="/api", tags=["screener"])
app.include_router(alerts.router,    prefix="/api", tags=["alerts"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/health", tags=["health"])
async def health_check():
    from app.core.cache import check_cache_health
    from app.core.database import check_db_health
    from fastapi.responses import JSONResponse
    from datetime import datetime

    cache_ok = await check_cache_health()
    db_ok    = await check_db_health()
    status   = "ok" if (cache_ok and db_ok) else "degraded"

    return JSONResponse(
        status_code=200 if status == "ok" else 503,
        content={
            "status":      status,
            "version":     "1.0.0",
            "environment": settings.ENVIRONMENT,
            "services":    {"cache": "ok" if cache_ok else "error",
                            "database": "ok" if db_ok else "error"},
            "timestamp":   datetime.utcnow().isoformat(),
            "disclaimer":  "Not financial advice",
        }
    )


@app.get("/", tags=["root"])
async def root():
    return {
        "name":       "Artha API",
        "version":    "1.0.0",
        "docs":       "/docs",
        "health":     "/health",
        "disclaimer": "Not financial advice. All data for informational purposes only.",
    }
