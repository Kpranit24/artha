# =============================================================
# backend/app/api/auth.py
# PURPOSE:  Auth endpoints — signup, login, logout, refresh
#
# USES: Supabase Auth when configured, local JWT in dev
#
# ENDPOINTS:
#   POST /auth/signup  → create account
#   POST /auth/login   → get access token
#   POST /auth/logout  → invalidate token
#   POST /auth/refresh → refresh expired token
#   GET  /auth/me      → get current user info
#
# LAST UPDATED: March 2026
# =============================================================

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx
from datetime import datetime, timedelta

from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter()


# ── REQUEST MODELS ────────────────────────────────────────

class SignupInput(BaseModel):
    email:    EmailStr
    password: str
    name:     Optional[str] = None

class LoginInput(BaseModel):
    email:    EmailStr
    password: str


# ── ENDPOINTS ─────────────────────────────────────────────

@router.post("/auth/signup")
async def signup(body: SignupInput):
    """
    Create a new account.
    Uses Supabase Auth if configured, else local JWT.
    """
    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        return await _supabase_signup(body)
    return await _local_signup(body)


@router.post("/auth/login")
async def login(body: LoginInput):
    """
    Sign in with email + password.
    Returns: { access_token, refresh_token, user }
    """
    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        return await _supabase_login(body)
    return await _local_login(body)


@router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(default=None)):
    """Invalidate current session"""
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"success": True})

    token = authorization.split(" ")[1]

    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/logout",
                headers={"Authorization": f"Bearer {token}",
                         "apikey": settings.SUPABASE_ANON_KEY},
            )

    return JSONResponse({"success": True, "message": "Logged out"})


@router.post("/auth/refresh")
async def refresh_token(body: dict):
    """Exchange refresh token for new access token"""
    refresh = body.get("refresh_token")
    if not refresh:
        raise HTTPException(status_code=400, detail="refresh_token required")

    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                headers={"apikey": settings.SUPABASE_ANON_KEY,
                         "Content-Type": "application/json"},
                json={"refresh_token": refresh},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        data = resp.json()
        return JSONResponse({
            "success":       True,
            "access_token":  data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in":    data.get("expires_in", 3600),
        })

    raise HTTPException(status_code=501, detail="Token refresh requires Supabase")


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user info"""
    return JSONResponse({
        "success": True,
        "data": {
            "id":    user["id"],
            "email": user["email"],
            "tier":  user["tier"],
        },
    })


# ── SUPABASE IMPLEMENTATIONS ──────────────────────────────

async def _supabase_signup(body: SignupInput) -> JSONResponse:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/signup",
            headers={"apikey": settings.SUPABASE_ANON_KEY,
                     "Content-Type": "application/json"},
            json={
                "email":    body.email,
                "password": body.password,
                "data":     {"name": body.name, "tier": "free"},
            },
        )

    if resp.status_code not in (200, 201):
        error = resp.json().get("msg", "Signup failed")
        raise HTTPException(status_code=400, detail=error)

    data = resp.json()
    return JSONResponse({
        "success": True,
        "message": "Account created. Check your email to confirm.",
        "user":    {"id": data.get("id"), "email": data.get("email")},
    })


async def _supabase_login(body: LoginInput) -> JSONResponse:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": settings.SUPABASE_ANON_KEY,
                     "Content-Type": "application/json"},
            json={"email": body.email, "password": body.password},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    data = resp.json()
    user = data.get("user", {})
    tier = user.get("user_metadata", {}).get("tier", "free")

    return JSONResponse({
        "success":       True,
        "access_token":  data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_in":    data.get("expires_in", 3600),
        "user": {
            "id":    user.get("id"),
            "email": user.get("email"),
            "tier":  tier,
        },
    })


# ── LOCAL JWT (dev fallback) ──────────────────────────────

_local_users: dict = {}   # In-memory store — dev only

async def _local_signup(body: SignupInput) -> JSONResponse:
    if body.email in _local_users:
        raise HTTPException(status_code=400, detail="Email already registered")
    import bcrypt
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    _local_users[body.email] = {"id": str(__import__("uuid").uuid4()), "email": body.email,
                                 "password": hashed, "name": body.name, "tier": "free"}
    return JSONResponse({"success": True, "message": "Account created (dev mode)"})


async def _local_login(body: LoginInput) -> JSONResponse:
    import bcrypt
    from jose import jwt

    user = _local_users.get(body.email)
    if not user or not bcrypt.checkpw(body.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    payload = {
        "sub":   user["id"],
        "email": user["email"],
        "tier":  user["tier"],
        "exp":   datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    return JSONResponse({
        "success":       True,
        "access_token":  token,
        "refresh_token": "dev-refresh-not-implemented",
        "expires_in":    3600,
        "user":          {"id": user["id"], "email": user["email"], "tier": user["tier"]},
    })
