# =============================================================
# backend/app/api/deps.py
# PURPOSE:  FastAPI dependencies — real Supabase auth + rate limiting
# LAST UPDATED: March 2026
# =============================================================

from fastapi import Request, HTTPException, Header
from typing import Optional
import time
import httpx

from app.core.config import settings
from app.core.cache import get_redis


async def get_current_user_optional(
    authorization: Optional[str] = Header(default=None)
) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await _verify_token(authorization.split(" ")[1])
    except Exception:
        return None


async def get_current_user(
    authorization: Optional[str] = Header(default=None)
) -> dict:
    user = await get_current_user_optional(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def _verify_token(token: str) -> dict:
    """
    Verify with Supabase if configured, else fall back to local JWT.
    SUPABASE_URL + SUPABASE_SERVICE_KEY in .env enables Supabase mode.
    """
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        d    = resp.json()
        tier = d.get("user_metadata", {}).get("tier", "free")
        return {"id": d["id"], "email": d["email"], "tier": tier}

    # Dev fallback — local JWT
    from jose import jwt, JWTError
    try:
        p = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return {"id": p.get("sub", "dev"), "email": p.get("email", "dev@local"), "tier": p.get("tier", "free")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def check_rate_limit(
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    redis  = get_redis()
    ident  = f"ip:{request.client.host}"
    if authorization and authorization.startswith("Bearer "):
        ident = f"tok:{authorization[7:20]}"

    tier = "free"
    if authorization:
        user = await get_current_user_optional(authorization)
        if user:
            tier = user.get("tier", "free")

    limit   = {"free": settings.RATE_LIMIT_FREE, "pro": settings.RATE_LIMIT_PRO, "vip": settings.RATE_LIMIT_VIP}.get(tier, settings.RATE_LIMIT_FREE)
    key     = f"rate:{ident}:{int(time.time()/60)}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)
    if current > limit:
        raise HTTPException(status_code=429, detail=f"Rate limit: {limit} req/min on {tier} tier")
