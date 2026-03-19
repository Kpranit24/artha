// =============================================================
// frontend/lib/api.ts
// PURPOSE:  Single source for ALL backend API calls
//           No component should call fetch() directly
//
// RULE:     Every API call goes through this file.
//           If the backend URL changes, fix it here only.
//           If auth headers change, fix it here only.
//
// USAGE:
//   import { api } from "@/lib/api"
//   const data = await api.heatmap.get({ index: "all", timeframe: "1d" })
//
// ERROR HANDLING:
//   All functions throw APIError on failure
//   Catch in components and show error state
//
// CACHING:
//   React Query handles client-side caching
//   Backend handles server-side Redis caching
//   Don't cache in this file — let React Query do it
//
// UPGRADE PATH:
//   If moving to GraphQL: replace fetch calls with Apollo Client
//   Keep the same function signatures — components won't change
//
// LAST UPDATED: March 2026
// =============================================================

import { APIResponse, HeatmapData, TickerData, InsightData, PortfolioData } from "@/types/market"

// ── CONFIG ────────────────────────────────────────────────
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// How often to refetch live data (milliseconds)
// 15s matches Perplexity Finance VIP refresh rate
// Increase to 60s to reduce API calls during development
export const REFETCH_INTERVAL_MS = 15_000


// ── ERROR CLASS ───────────────────────────────────────────

export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public endpoint?: string
  ) {
    super(message)
    this.name = "APIError"
  }
}


// ── BASE FETCHER ──────────────────────────────────────────

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<APIResponse<T>> {
  const url = `${BASE_URL}${endpoint}`

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  }

  // Add auth token if user is logged in
  const token = getAuthToken()
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`
  }

  let response: Response
  try {
    response = await fetch(url, { ...options, headers })
  } catch (error) {
    // Network error — backend is down or unreachable
    throw new APIError(
      "Cannot reach server. Check your connection.",
      0,
      endpoint
    )
  }

  const data = await response.json()

  if (!response.ok) {
    throw new APIError(
      data.detail || `Request failed (${response.status})`,
      response.status,
      endpoint
    )
  }

  return data
}


// ── HEATMAP ───────────────────────────────────────────────

interface HeatmapParams {
  index?: string      // "all" | "nifty50" | "nasdaq" | "crypto"
  timeframe?: string  // "1d" | "1w" | "1m" | "ytd"
}

async function getHeatmap(params: HeatmapParams = {}): Promise<HeatmapData> {
  const query = new URLSearchParams({
    index:     params.index     || "all",
    timeframe: params.timeframe || "1d",
  })

  const response = await fetchAPI<HeatmapData>(`/api/heatmap?${query}`)

  if (!response.success || !response.data) {
    throw new APIError("Heatmap data unavailable")
  }

  return response.data
}


// ── TICKER ────────────────────────────────────────────────

interface TickerParams {
  symbol:     string
  market:     "india" | "us" | "crypto"
  timeframe?: string
  insight?:   boolean   // Include AI insight (slower, costs money)
}

async function getTicker(params: TickerParams): Promise<{
  ticker: TickerData
  ohlcv: Array<{ timestamp: string; open: number; high: number; low: number; close: number; volume: number }>
  insight?: InsightData
}> {
  const query = new URLSearchParams({
    market:    params.market,
    timeframe: params.timeframe || "1m",
    insight:   String(params.insight ?? true),
  })

  const response = await fetchAPI(`/api/ticker/${params.symbol}?${query}`)

  if (!response.success || !response.data) {
    throw new APIError(`No data for ${params.symbol}`)
  }

  return response.data as any
}


// ── SCREENER ──────────────────────────────────────────────

interface ScreenerParams {
  market?:    "all" | "india" | "us" | "crypto"
  filter?:    "gainers" | "losers" | "volume" | "cap" | "ath"
  timeframe?: string
  limit?:     number
}

async function getScreener(params: ScreenerParams = {}): Promise<TickerData[]> {
  const query = new URLSearchParams({
    market:    params.market    || "all",
    filter:    params.filter    || "gainers",
    timeframe: params.timeframe || "1d",
    limit:     String(params.limit || 20),
  })

  const response = await fetchAPI<TickerData[]>(`/api/screener?${query}`)

  if (!response.success || !response.data) {
    return []
  }

  return response.data
}


// ── PORTFOLIO ─────────────────────────────────────────────

async function getPortfolio(): Promise<PortfolioData> {
  // Requires authentication
  const response = await fetchAPI<PortfolioData>("/api/portfolio")

  if (!response.success || !response.data) {
    throw new APIError("Portfolio data unavailable. Are you logged in?")
  }

  return response.data
}

async function updateHolding(holding: {
  symbol:   string
  market:   string
  quantity: number
  avg_cost: number
  currency: string
}): Promise<void> {
  await fetchAPI("/api/portfolio/holdings", {
    method: "POST",
    body:   JSON.stringify(holding),
  })
}


// ── ALERTS ────────────────────────────────────────────────

async function createAlert(alert: {
  symbol:    string
  condition: "above" | "below"
  price:     number
}): Promise<{ id: string }> {
  const response = await fetchAPI<{ id: string }>("/api/alerts", {
    method: "POST",
    body:   JSON.stringify(alert),
  })

  if (!response.success || !response.data) {
    throw new APIError("Failed to create alert")
  }

  return response.data
}


// ── HEALTH CHECK ──────────────────────────────────────────

async function checkHealth(): Promise<{
  status: "ok" | "degraded"
  services: { cache: string; database: string }
}> {
  const response = await fetch(`${BASE_URL}/health`)
  return response.json()
}


// ── AUTH HELPERS ──────────────────────────────────────────

function getAuthToken(): string | null {
  // NOTE: Store token in memory, not localStorage
  // localStorage is accessible to XSS attacks
  // For production: use httpOnly cookies via Supabase auth
  // This is a simplified version for development
  if (typeof window === "undefined") return null
  return sessionStorage.getItem("auth_token")
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return
  sessionStorage.setItem("auth_token", token)
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") return
  sessionStorage.removeItem("auth_token")
}


// ── EXPORTED API OBJECT ───────────────────────────────────
// Use this everywhere:
//   import { api } from "@/lib/api"
//   const data = await api.heatmap.get()

export const api = {
  heatmap: {
    get: getHeatmap,
  },
  ticker: {
    get: getTicker,
  },
  screener: {
    get: getScreener,
  },
  portfolio: {
    get:           getPortfolio,
    updateHolding: updateHolding,
  },
  alerts: {
    create: createAlert,
  },
  health: {
    check: checkHealth,
  },
} as const
