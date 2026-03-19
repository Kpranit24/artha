# =============================================================
# backend/app/agents/insight_agent.py
# PURPOSE:  AI-powered market insights
#
# AI PROVIDER PRIORITY:
#   1. Groq (free — 14,400 req/day, ~0.5s response)
#      Model: llama-3.3-70b-versatile
#      Get key: console.groq.com → API Keys → Create
#
#   2. Claude (paid — fallback when Groq unavailable)
#      Model: claude-sonnet-4-6
#      Get key: console.anthropic.com
#
#   3. Demo insight (no key — static placeholder text)
#
# AUTO-DETECTION:
#   Set GROQ_API_KEY in .env → uses Groq automatically
#   Set CLAUDE_API_KEY in .env → uses Claude as fallback
#   Set neither → returns demo insight (no AI calls)
#
# COST:
#   Groq:  $0 (free tier: 14,400 req/day, 6,000 tokens/min)
#   Claude: ~$0.003/insight (only used if Groq fails)
#
# CACHE:
#   1 hour TTL — same ticker rarely needs fresh insight every minute
#   1000 users viewing BTC = 1 Groq call/hour, not 1000
#
# LAST UPDATED: March 2026
# =============================================================

import json
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.cache import get_with_cache, insight_key
from app.models.market import TickerData


# ── MAIN ENTRY POINT ──────────────────────────────────────

async def generate_insight(
    ticker: TickerData,
    news_headlines: list[str] = None,
) -> dict:
    """
    Generate AI market insight for a ticker.
    Tries Groq first (free), falls back to Claude, then demo.

    Result is cached for 1 hour — cheap to run at scale.
    """
    if not settings.ENABLE_AI_INSIGHTS:
        return _demo_insight(ticker)

    cache_key = insight_key(ticker.symbol)
    return await get_with_cache(
        key=cache_key,
        fetch_fn=lambda: _generate(ticker, news_headlines),
        ttl=settings.CACHE_TTL_INSIGHTS  # 1 hour
    )


async def _generate(ticker: TickerData, news_headlines: list[str] = None) -> dict:
    """Try each provider in order until one works"""

    # Try Groq first (free)
    if settings.GROQ_API_KEY:
        try:
            return await _call_groq(ticker, news_headlines)
        except Exception as e:
            print(f"Groq failed for {ticker.symbol}: {e} — trying Claude")

    # Try Claude fallback (paid)
    if settings.CLAUDE_API_KEY:
        try:
            return await _call_claude(ticker, news_headlines)
        except Exception as e:
            print(f"Claude failed for {ticker.symbol}: {e} — using demo")

    # No AI key configured — return demo insight
    return _demo_insight(ticker)


# ── GROQ IMPLEMENTATION ───────────────────────────────────

async def _call_groq(ticker: TickerData, news_headlines: list[str] = None) -> dict:
    """
    Call Groq API using OpenAI-compatible endpoint.
    Groq uses same API format as OpenAI — very easy to integrate.

    Free tier limits:
        6,000 tokens/minute
        14,400 requests/day
        500 requests/minute
    """
    from openai import AsyncOpenAI  # Groq uses OpenAI-compatible client

    client = AsyncOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

    prompt = _build_prompt(ticker, news_headlines)

    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a market data analyst providing factual, concise summaries. "
                    "Explain price movements based on available data. "
                    "Never recommend buying, selling, or any financial action. "
                    "Always respond in valid JSON format only. No markdown, no explanation outside JSON."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,      # Low temperature = consistent, factual responses
        max_tokens=600,       # Keep short — users read this on mobile
        response_format={"type": "json_object"},  # Force JSON output
    )

    raw = response.choices[0].message.content
    return _parse_and_enrich(raw, ticker, provider="groq")


# ── CLAUDE FALLBACK ───────────────────────────────────────

async def _call_claude(ticker: TickerData, news_headlines: list[str] = None) -> dict:
    """
    Claude fallback — only called if Groq fails or is unavailable.
    Add CLAUDE_API_KEY to .env to enable.
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
    prompt = _build_prompt(ticker, news_headlines)

    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=settings.CLAUDE_MAX_TOKENS,
        system=(
            "You are a market data analyst. Explain price movements factually. "
            "Never recommend financial actions. "
            "Respond ONLY in valid JSON format."
        ),
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown code blocks if present
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return _parse_and_enrich(raw, ticker, provider="claude")


# ── SHARED PROMPT ─────────────────────────────────────────

def _build_prompt(ticker: TickerData, news_headlines: list[str] = None) -> str:
    """Builds the analysis prompt — same for all AI providers"""

    change_direction = "up" if (ticker.change_1d or 0) >= 0 else "down"
    change_abs       = abs(ticker.change_1d or 0)
    currency_symbol  = "₹" if ticker.currency.value == "INR" else "$"

    news_context = ""
    if news_headlines:
        news_context = "\nRecent news:\n" + "\n".join(f"- {h}" for h in news_headlines[:5])

    return f"""Analyze this market data and provide a concise insight:

Ticker: {ticker.symbol} ({ticker.name})
Market: {ticker.market.value}
Price: {currency_symbol}{ticker.price:,.2f}
Change today: {change_direction} {change_abs:.2f}%
Change 7d: {f"{ticker.change_7d:+.2f}%" if ticker.change_7d else "N/A"}
Volume: {f"${ticker.volume_24h:,.0f}" if ticker.volume_24h else "N/A"}
{f"P/E ratio: {ticker.pe_ratio}" if ticker.pe_ratio else ""}
{news_context}

Respond in this exact JSON format:
{{
    "headline": "One sentence explaining the main movement (max 15 words)",
    "summary": "2-3 sentences of analysis",
    "bull_case": "One sentence: why it might go higher",
    "bear_case": "One sentence: why it might go lower",
    "key_drivers": ["driver 1", "driver 2", "driver 3"],
    "sentiment": "bullish",
    "confidence": "medium"
}}

sentiment must be: bullish, bearish, or neutral
confidence must be: high, medium, or low
Be factual. Do not recommend buying or selling."""


# ── PARSE RESPONSE ────────────────────────────────────────

def _parse_and_enrich(raw: str, ticker: TickerData, provider: str) -> dict:
    """Parse AI response JSON and add metadata"""
    try:
        parsed = json.loads(raw.strip())
    except json.JSONDecodeError:
        # Try to extract JSON if wrapped in text
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            return _demo_insight(ticker)

    # Ensure all required fields exist
    parsed.setdefault("headline",    f"{ticker.symbol} price movement analysis")
    parsed.setdefault("summary",     "Market analysis unavailable.")
    parsed.setdefault("bull_case",   "Positive momentum could continue.")
    parsed.setdefault("bear_case",   "Broader market conditions may weigh.")
    parsed.setdefault("key_drivers", ["Market momentum", "Sector trends", "Volume activity"])
    parsed.setdefault("sentiment",   "neutral")
    parsed.setdefault("confidence",  "low")

    # Add metadata
    parsed["symbol"]       = ticker.symbol
    parsed["disclaimer"]   = "Not financial advice. For informational purposes only."
    parsed["generated_at"] = datetime.utcnow().isoformat()
    parsed["model_used"]   = f"{provider}:{settings.GROQ_MODEL if provider == 'groq' else settings.CLAUDE_MODEL}"
    parsed["provider"]     = provider

    return parsed


# ── DEMO INSIGHT (no API key) ─────────────────────────────

def _demo_insight(ticker: TickerData) -> dict:
    """
    Returned when no AI key is configured or all providers fail.
    Shows a basic insight based on price direction alone.
    """
    is_up    = (ticker.change_1d or 0) >= 0
    pct      = abs(ticker.change_1d or 0)
    movement = f"{'gained' if is_up else 'declined'} {pct:.2f}% today"

    return {
        "symbol":       ticker.symbol,
        "headline":     f"{ticker.symbol} {movement}",
        "summary":      (
            f"{ticker.name} has {movement}. "
            "Add a GROQ_API_KEY to .env for detailed AI analysis — it's free at console.groq.com"
        ),
        "bull_case":    "Add GROQ_API_KEY for bull case analysis.",
        "bear_case":    "Add GROQ_API_KEY for bear case analysis.",
        "key_drivers":  ["No AI key configured", "Add GROQ_API_KEY to .env", "Free at console.groq.com"],
        "sentiment":    "bullish" if is_up else "bearish",
        "confidence":   "low",
        "disclaimer":   "Not financial advice. For informational purposes only.",
        "generated_at": datetime.utcnow().isoformat(),
        "model_used":   "demo",
        "provider":     "demo",
    }
