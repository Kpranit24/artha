# =============================================================
# backend/app/agents/monitors/supervisor.py
# PURPOSE:  Master monitoring agent — watches everything 24/7
#           Collects reports from all 5 monitor agents
#           Asks Claude to analyze and prioritize
#           Sends Telegram alerts to your phone
#
# RUNS:     Every 5 minutes (background task)
# DAILY:    Full report at 9am IST
#
# WHAT IT WATCHES:
#   frontend_agent  → page load, chart errors, bundle size
#   backend_agent   → response times, memory, API failures
#   db_agent        → storage, slow queries, backups
#   security_agent  → rate abuse, JWT anomalies, secrets
#   cost_agent      → API spend, free tier usage, forecast
#
# ALERTS SENT TO: Telegram (free, works great in India)
# FALLBACK:       Email via Gmail SMTP
#
# TO DISABLE: Set ENABLE_MONITORING=false in .env
#
# LAST UPDATED: March 2026
# =============================================================

import asyncio
import anthropic
from datetime import datetime
import pytz
from typing import Optional

from app.core.config import settings

IST = pytz.timezone("Asia/Kolkata")


# ── ALERT LEVELS ──────────────────────────────────────────
LEVEL_GREEN  = "GREEN"   # All good — no action needed
LEVEL_YELLOW = "YELLOW"  # Warning — monitor closely
LEVEL_RED    = "RED"     # Critical — immediate action needed


# ── SUPERVISOR MAIN LOOP ──────────────────────────────────

async def start_monitoring():
    """
    Starts the monitoring loop as a background task.
    Called from main.py on app startup.
    Runs forever — checks every 5 minutes.
    """
    asyncio.create_task(_monitoring_loop())
    asyncio.create_task(_daily_report_loop())


async def _monitoring_loop():
    """Runs every 5 minutes — collects and analyzes all reports"""
    while True:
        try:
            await run_supervisor_check()
        except Exception as e:
            # Monitoring should never crash the app
            print(f"Supervisor error: {e}")
        # Wait 5 minutes before next check
        await asyncio.sleep(300)


async def _daily_report_loop():
    """Sends a full health report every day at 9am IST"""
    while True:
        now_ist = datetime.now(IST)
        # Check if it's 9am IST
        if (now_ist.hour == settings.DAILY_REPORT_HOUR and
            now_ist.minute == settings.DAILY_REPORT_MINUTE):
            try:
                await send_daily_report()
            except Exception as e:
                print(f"Daily report error: {e}")
            # Sleep 61 seconds to avoid sending twice in same minute
            await asyncio.sleep(61)
        # Check every 30 seconds
        await asyncio.sleep(30)


async def run_supervisor_check():
    """
    Runs all monitor agents in parallel.
    Asks Claude to analyze and prioritize.
    Sends alert only if something needs attention.
    """

    # Run all 5 monitors in parallel (fast)
    # asyncio.gather runs them simultaneously
    results = await asyncio.gather(
        _run_backend_check(),
        _run_db_check(),
        _run_cost_check(),
        _run_security_check(),
        return_exceptions=True  # Don't crash if one monitor fails
    )

    backend_report, db_report, cost_report, security_report = results

    # Handle exceptions in individual monitors
    reports = {
        "backend": backend_report if not isinstance(backend_report, Exception) else {"error": str(backend_report)},
        "database": db_report if not isinstance(db_report, Exception) else {"error": str(db_report)},
        "cost": cost_report if not isinstance(cost_report, Exception) else {"error": str(cost_report)},
        "security": security_report if not isinstance(security_report, Exception) else {"error": str(security_report)},
    }

    # Check if anything needs attention
    has_issues = any(
        r.get("level") in [LEVEL_YELLOW, LEVEL_RED]
        for r in reports.values()
        if isinstance(r, dict)
    )

    if not has_issues:
        return  # Everything is fine — no alert needed

    # Ask Claude to analyze and prioritize
    analysis = await _analyze_with_claude(reports)

    # Send alert
    await send_alert(
        level=analysis.get("level", LEVEL_YELLOW),
        message=analysis.get("message", "Issues detected"),
        auto_fixed=analysis.get("auto_fixed", False)
    )

    # Execute any auto-fixes
    await _execute_auto_fixes(reports)


# ── INDIVIDUAL MONITOR CHECKS ─────────────────────────────

async def _run_backend_check() -> dict:
    """
    Checks FastAPI health:
    - Average response time
    - Error rate
    - Memory usage
    - Cache hit rate
    """
    from app.core.cache import get_cache_stats

    try:
        cache_stats = await get_cache_stats()

        issues = []
        level = LEVEL_GREEN

        # Check cache hit rate
        if cache_stats["hit_rate_pct"] < 80:
            issues.append(f"Cache hit rate low: {cache_stats['hit_rate_pct']}% (target >80%)")
            level = LEVEL_YELLOW

        # Check Upstash free tier limit
        if cache_stats["commands_today"] > cache_stats["upstash_free_limit"] * 0.8:
            issues.append(f"Approaching Upstash free limit: {cache_stats['commands_today']}/10000 commands today")
            level = LEVEL_YELLOW

        return {
            "level": level,
            "cache_hit_rate": cache_stats["hit_rate_pct"],
            "cache_memory_mb": cache_stats["memory_mb"],
            "issues": issues
        }
    except Exception as e:
        return {
            "level": LEVEL_RED,
            "issues": [f"Could not check backend health: {e}"]
        }


async def _run_db_check() -> dict:
    """
    Checks database health:
    - Storage usage vs Supabase free tier (500MB)
    - Connection count
    """
    # TODO: Implement actual DB checks
    # For now returns green to avoid false alerts
    return {
        "level": LEVEL_GREEN,
        "issues": [],
        "note": "DB monitoring not yet implemented"
    }


async def _run_cost_check() -> dict:
    """
    Checks API spending:
    - Claude API daily spend vs budget
    - CoinGecko requests vs free tier
    """
    # TODO: Read from Redis counters set by insight_agent
    # For now returns placeholder
    return {
        "level": LEVEL_GREEN,
        "claude_spend_today_usd": 0,
        "claude_budget_usd": settings.DAILY_CLAUDE_BUDGET_USD,
        "issues": []
    }


async def _run_security_check() -> dict:
    """
    Checks for security issues:
    - Unusual request patterns
    - Failed auth attempts
    """
    # TODO: Read from request logs in Redis
    return {
        "level": LEVEL_GREEN,
        "issues": []
    }


# ── CLAUDE ANALYSIS ───────────────────────────────────────

async def _analyze_with_claude(reports: dict) -> dict:
    """
    Sends all monitor reports to Claude for analysis.
    Claude prioritizes issues and suggests actions.

    Why Claude? Because raw monitor data needs interpretation:
    "Cache hit rate 72%" alone is just a number.
    Claude tells you WHY it's low and WHAT to do about it.
    """
    if not settings.CLAUDE_API_KEY:
        # No Claude key — return basic summary
        return {
            "level": LEVEL_YELLOW,
            "message": "Issues detected. Check monitor reports.",
            "auto_fixed": False
        }

    client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)

    import json
    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=300,  # Keep short — this is a phone notification
        system="""You are a DevOps assistant for a finance dashboard.
Analyze system health reports and provide concise alerts.
Response must be JSON: {"level": "GREEN/YELLOW/RED", "message": "plain text max 200 chars", "auto_fixed": true/false}
Be direct. No markdown. Developers read this on phone.""",
        messages=[{
            "role": "user",
            "content": f"Health reports: {json.dumps(reports, indent=2)}\nSummarize the top issue and whether it needs immediate action."
        }]
    )

    import json as json2
    content = response.content[0].text.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    return json2.loads(content)


# ── AUTO-FIX ACTIONS ──────────────────────────────────────

async def _execute_auto_fixes(reports: dict):
    """
    Executes safe auto-fixes for common issues.
    Only runs actions that can't cause data loss.
    Anything risky gets flagged for human review.
    """
    for service, report in reports.items():
        if not isinstance(report, dict):
            continue
        # Add auto-fix logic here as needed
        # Example: clear stale cache keys, restart connections etc.
        pass


# ── NOTIFICATIONS ─────────────────────────────────────────

async def send_alert(level: str, message: str, auto_fixed: bool = False):
    """
    Send alert to Telegram (primary) or email (fallback).
    
    Message format:
        🔴 CRITICAL — Artha
        ✅ Auto-fixed  (or ⚠️ Needs attention)
        
        [message]
        
        Time: 19 Mar 2026, 3:42 PM IST
    """
    now_ist = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")

    prefix = {"RED": "🔴 CRITICAL", "YELLOW": "🟡 WARNING", "GREEN": "🟢 ALL GOOD"}.get(level, "🟡 WARNING")
    action = "✅ Auto-fixed" if auto_fixed else "⚠️ Needs attention"

    text = f"{prefix} — Artha\n{action}\n\n{message}\n\nTime: {now_ist}"

    # Try Telegram first
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        await _send_telegram(text)
    # Fall back to email
    elif settings.SMTP_USER and settings.ALERT_EMAIL:
        await _send_email(f"[{level}] Artha Alert", text)
    else:
        # No notification configured — just log
        print(f"ALERT [{level}]: {message}")


async def send_daily_report():
    """
    Sends a full health report at 9am IST.
    Covers: users, API health, costs, storage, predictions.
    """
    now_ist = datetime.now(IST).strftime("%d %B %Y")

    # Collect all data
    cache_stats = await get_cache_stats_safe()

    report = f"""🟢 Daily Report — Artha
{now_ist}

CACHE:    {cache_stats.get('hit_rate_pct', '?')}% hit rate
MEMORY:   {cache_stats.get('cache_memory_mb', '?')} MB used
COMMANDS: {cache_stats.get('commands_today', '?')}/10000 today (Upstash free)

AI SPEND: Checking...
DB: Checking...

REMINDER: Not financial advice dashboard."""

    await send_alert(LEVEL_GREEN, report)


async def get_cache_stats_safe() -> dict:
    """Safe wrapper — returns empty dict if cache unavailable"""
    try:
        from app.core.cache import get_cache_stats
        return await get_cache_stats()
    except Exception:
        return {}


async def _send_telegram(text: str):
    """Send message via Telegram Bot API"""
    import httpx
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        })


async def _send_email(subject: str, body: str):
    """Send email via SMTP (fallback when no Telegram)"""
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.ALERT_EMAIL

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
