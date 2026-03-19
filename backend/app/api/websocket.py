# =============================================================
# backend/app/api/websocket.py
# PURPOSE:  WebSocket endpoint for live price streaming
#
# ENDPOINT: WS /ws/prices/{user_id}
#
# HOW IT WORKS:
#   1. Client connects to /ws/prices/{user_id}
#   2. Server sends current prices immediately on connect
#   3. Server checks prices every 15 seconds
#   4. Only sends update if price changed > 0.5% (Δprice threshold)
#   5. Client receives: { event, ticker, price, pct_change, timestamp }
#
# WHY 0.5% THRESHOLD:
#   Prevents flooding client with tiny price movements
#   Matches Perplexity Finance's WebSocket logic from architecture doc
#   Saves bandwidth — only meaningful moves trigger an update
#
# CONNECTIONS:
#   Max 50 tickers per connection (from architecture doc)
#   Each user subscribes to their watchlist + portfolio symbols
#
# UPGRADE PATH:
#   At 5K+ concurrent users, replace asyncio loop with:
#   Redis Pub/Sub → FastAPI WebSocket broadcaster
#   One Redis channel per ticker, many subscribers
#   Zero code changes to frontend — same message format
#
# AI AGENT MONITORS:
#   backend_agent → tracks active connections + memory usage
#   security_agent → alerts on unusual connection patterns
#
# LAST UPDATED: March 2026
# =============================================================

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import asyncio
import json
from datetime import datetime

from app.data.sources import get_prices
from app.models.market import Timeframe


router = APIRouter()


# ── CONNECTION MANAGER ────────────────────────────────────

class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Tracks which symbols each connection subscribes to.

    UPGRADE PATH:
        Replace _connections dict with Redis Pub/Sub at 5K+ users
        Current: O(connections) broadcast
        Redis:   O(1) publish, consumers auto-route
    """

    def __init__(self):
        # user_id → WebSocket connection
        self._connections: Dict[str, WebSocket] = {}
        # user_id → set of subscribed symbols
        self._subscriptions: Dict[str, Set[str]] = {}
        # symbol → last known price (for delta detection)
        self._last_prices: Dict[str, float] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[user_id] = websocket
        self._subscriptions[user_id] = set()
        print(f"WS connected: {user_id} ({len(self._connections)} total)")

    def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)
        self._subscriptions.pop(user_id, None)
        print(f"WS disconnected: {user_id} ({len(self._connections)} total)")

    def subscribe(self, user_id: str, symbols: list[str]):
        """Subscribe user to price updates for these symbols"""
        if user_id in self._subscriptions:
            # Max 50 tickers per connection
            limited = symbols[:50]
            self._subscriptions[user_id] = set(s.upper() for s in limited)

    async def send_to(self, user_id: str, message: dict):
        """Send message to a specific connection"""
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast_price_update(self, symbol: str, price: float, change_pct: float):
        """
        Send price update to all connections subscribed to this symbol.
        Only called when price moved > 0.5%.
        """
        message = {
            "event":      "price_update",
            "ticker":     symbol,
            "price":      price,
            "pct_change": round(change_pct, 2),
            "timestamp":  datetime.utcnow().isoformat(),
        }

        # Find all connections subscribed to this symbol
        for user_id, symbols in list(self._subscriptions.items()):
            if symbol in symbols:
                await self.send_to(user_id, message)

    def has_price_moved(self, symbol: str, new_price: float) -> bool:
        """
        Returns True if price moved > 0.5% since last check.
        This is the Δprice threshold from the architecture doc.
        """
        last = self._last_prices.get(symbol)
        if last is None:
            self._last_prices[symbol] = new_price
            return True  # First price — always send

        change_pct = abs((new_price - last) / last * 100)
        if change_pct > 0.5:
            self._last_prices[symbol] = new_price
            return True

        return False

    @property
    def active_symbols(self) -> Set[str]:
        """All symbols currently being watched by any connection"""
        symbols = set()
        for subs in self._subscriptions.values():
            symbols.update(subs)
        return symbols

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# ── GLOBAL MANAGER INSTANCE ───────────────────────────────
manager = ConnectionManager()


# ── WEBSOCKET ENDPOINT ────────────────────────────────────

@router.websocket("/ws/prices/{user_id}")
async def websocket_prices(
    websocket: WebSocket,
    user_id: str,
    symbols: str = Query(
        default="BTC,ETH,SOL",
        description="Comma-separated symbols to watch. Max 50."
    ),
):
    """
    WebSocket endpoint for live price streaming.

    Connect: ws://localhost:8000/ws/prices/user123?symbols=BTC,ETH,INFY

    Message types received by client:
        { event: "connected",     message: "..." }
        { event: "price_update",  ticker, price, pct_change, timestamp }
        { event: "subscribed",    symbols: [...] }
        { event: "heartbeat",     timestamp }
        { event: "error",         message }
    """

    await manager.connect(user_id, websocket)

    try:
        # Parse and subscribe to symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        manager.subscribe(user_id, symbol_list)

        # Send confirmation
        await manager.send_to(user_id, {
            "event":   "connected",
            "message": f"Connected. Watching {len(symbol_list)} symbols.",
            "symbols": symbol_list,
        })

        # Send current prices immediately on connect
        await _send_current_prices(user_id, symbol_list)

        # Message loop — handle incoming messages + send heartbeat
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(user_id)
        )

        try:
            while True:
                # Wait for messages from client
                # Client can send: { "action": "subscribe", "symbols": [...] }
                raw = await websocket.receive_text()
                message = json.loads(raw)

                if message.get("action") == "subscribe":
                    new_symbols = message.get("symbols", [])
                    manager.subscribe(user_id, new_symbols)
                    await manager.send_to(user_id, {
                        "event":   "subscribed",
                        "symbols": new_symbols,
                    })

        finally:
            heartbeat_task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error for {user_id}: {e}")
    finally:
        manager.disconnect(user_id)


# ── BACKGROUND PRICE CHECKER ──────────────────────────────

async def start_price_broadcast_loop():
    """
    Background task that polls prices and broadcasts changes.
    Started from main.py on app startup.

    Runs every 15 seconds — checks all actively watched symbols.
    Only broadcasts when price moves > 0.5%.

    NOTE TO AI AGENTS:
        If this loop stops, WebSocket updates stop.
        backend_agent should alert if no broadcasts in > 60 seconds
        while connections are active.
    """
    while True:
        try:
            if manager.connection_count > 0 and manager.active_symbols:
                await _check_and_broadcast()
        except Exception as e:
            print(f"Price broadcast error: {e}")

        # Wait 15 seconds before next check
        await asyncio.sleep(15)


async def _check_and_broadcast():
    """
    Fetches current prices for all watched symbols.
    Broadcasts to subscribers when price moves > 0.5%.
    """
    symbols = list(manager.active_symbols)
    if not symbols:
        return

    # Group by market for efficient fetching
    crypto_syms = [s for s in symbols if _is_crypto(s)]
    india_syms  = [s for s in symbols if _is_india(s)]
    us_syms     = [s for s in symbols if not _is_crypto(s) and not _is_india(s)]

    # Fetch in parallel
    results = await asyncio.gather(
        get_prices(crypto_syms, "crypto", Timeframe.ONE_DAY) if crypto_syms else asyncio.coroutine(lambda: [])(),
        get_prices(india_syms,  "india",  Timeframe.ONE_DAY) if india_syms  else asyncio.coroutine(lambda: [])(),
        get_prices(us_syms,     "us",     Timeframe.ONE_DAY) if us_syms     else asyncio.coroutine(lambda: [])(),
        return_exceptions=True
    )

    # Broadcast price updates for moved symbols
    for result in results:
        if isinstance(result, list):
            for ticker in result:
                if manager.has_price_moved(ticker.symbol, ticker.price):
                    await manager.broadcast_price_update(
                        symbol=ticker.symbol,
                        price=ticker.price,
                        change_pct=ticker.change_1d or 0,
                    )


async def _send_current_prices(user_id: str, symbols: list[str]):
    """Send current prices to a newly connected user"""
    try:
        crypto = [s for s in symbols if _is_crypto(s)]
        india  = [s for s in symbols if _is_india(s)]
        us     = [s for s in symbols if not _is_crypto(s) and not _is_india(s)]

        all_tickers = []
        results = await asyncio.gather(
            get_prices(crypto, "crypto", Timeframe.ONE_DAY) if crypto else asyncio.coroutine(lambda: [])(),
            get_prices(india,  "india",  Timeframe.ONE_DAY) if india  else asyncio.coroutine(lambda: [])(),
            get_prices(us,     "us",     Timeframe.ONE_DAY) if us     else asyncio.coroutine(lambda: [])(),
            return_exceptions=True
        )
        for r in results:
            if isinstance(r, list):
                all_tickers.extend(r)

        await manager.send_to(user_id, {
            "event":   "initial_prices",
            "prices":  [
                {
                    "ticker":     t.symbol,
                    "price":      t.price,
                    "pct_change": t.change_1d or 0,
                    "is_live":    t.is_live,
                }
                for t in all_tickers
            ],
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        print(f"Initial price send error: {e}")


async def _heartbeat_loop(user_id: str):
    """Send heartbeat every 30 seconds to keep connection alive"""
    while True:
        await asyncio.sleep(30)
        await manager.send_to(user_id, {
            "event":     "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
        })


def _is_crypto(symbol: str) -> bool:
    """Rough check if symbol is a crypto ticker"""
    crypto_symbols = {
        "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA",
        "AVAX", "LINK", "DOT", "UNI", "LTC", "SHIB", "TON", "SUI", "APT"
    }
    return symbol.upper() in crypto_symbols


def _is_india(symbol: str) -> bool:
    """Check if symbol is an India stock (ends in .NS or is known NSE ticker)"""
    return symbol.endswith(".NS") or symbol.endswith(".BO")
