// =============================================================
// frontend/types/market.ts
// PURPOSE:  TypeScript types for ALL market data in the frontend
//
// RULE:     Every piece of data from the backend must match
//           one of these types before being used in components.
//           This catches backend API changes at compile time.
//
// SYNC:     Keep in sync with backend/app/models/market.py
//           If you add a field in Python, add it here too.
//
// ADDING A NEW FIELD:
//   1. Add to the interface below (optional with ?)
//   2. Add to backend/app/models/market.py
//   3. TypeScript will show errors where it's used
//      if you forgot to handle it
//
// LAST UPDATED: March 2026
// =============================================================

// ── ENUMS ─────────────────────────────────────────────────

export type Market = "india" | "us" | "crypto";

export type Currency = "INR" | "USD";

export type DataSource =
  | "coingecko"
  | "yahoo"
  | "yfinance"
  | "alpha_vantage"
  | "polygon"
  | "twelve_data"
  | "static_demo";

export type Timeframe = "1d" | "1w" | "1m" | "3m" | "6m" | "1y" | "ytd" | "5y";

export type Sentiment = "bullish" | "bearish" | "neutral";

export type AlertLevel = "GREEN" | "YELLOW" | "RED";


// ── CORE TICKER DATA ──────────────────────────────────────

export interface TickerData {
  // Identity
  symbol: string;         // "TCS.NS", "BTC", "AAPL"
  name: string;           // "Tata Consultancy Services"
  market: Market;
  currency: Currency;

  // Price
  price: number;
  price_open?: number;
  price_high?: number;
  price_low?: number;
  price_close?: number;

  // Changes (percentage — 1.4 = +1.4%)
  change_1d?: number;
  change_7d?: number;
  change_30d?: number;
  change_ytd?: number;

  // Volume and market cap
  volume_24h?: number;
  market_cap?: number;    // Always USD for comparability

  // Fundamentals (equities only)
  pe_ratio?: number;
  pb_ratio?: number;
  dividend_yield?: number;
  beta?: number;
  revenue_growth?: number;

  // Sparkline (7 days of prices for mini charts)
  sparkline?: number[];

  // ATH
  ath?: number;
  ath_change_pct?: number;

  // Metadata
  source: DataSource;
  is_live: boolean;
  fetched_at: string;       // ISO string
  delayed_by_seconds: number;
}

// Helper: is this data stale?
export const isDelayed = (ticker: TickerData): boolean => {
  const age = (Date.now() - new Date(ticker.fetched_at).getTime()) / 1000;
  return age > 60;
};

// Helper: formatted price string
export const formatPrice = (ticker: TickerData): string => {
  const symbol = ticker.currency === "INR" ? "₹" : "$";
  return `${symbol}${ticker.price.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

// Helper: color class based on change
export const changeColor = (change?: number): string => {
  if (!change) return "text-muted-foreground";
  return change >= 0 ? "text-green-600" : "text-red-600";
};


// ── OHLCV (candlestick charts) ────────────────────────────

export interface OHLCVPoint {
  timestamp: string;  // ISO string
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCVData {
  symbol: string;
  timeframe: Timeframe;
  candles: OHLCVPoint[];
  source: DataSource;
  fetched_at: string;
}


// ── HEATMAP ───────────────────────────────────────────────

export interface HeatmapBubble {
  symbol: string;
  name: string;
  market: Market;
  x: number;          // Market cap rank
  y: number;          // % change
  size: number;       // Bubble radius
  color: string;      // Hex color
  price: number;
  change_pct: number;
  market_cap?: number;
  sector?: string;
}

export interface HeatmapData {
  bubbles: HeatmapBubble[];
  timeframe: Timeframe;
  index: string;
  fetched_at: string;
  is_live: boolean;
}


// ── AI INSIGHTS ───────────────────────────────────────────

export interface InsightData {
  symbol: string;
  headline: string;       // 1 sentence
  summary: string;        // 2-3 sentences
  bull_case: string;
  bear_case: string;
  key_drivers: string[];  // Top 3 reasons
  sentiment: Sentiment;
  confidence: "high" | "medium" | "low";
  disclaimer: string;     // Always shown
  generated_at: string;
  model_used: string;
}


// ── PORTFOLIO ─────────────────────────────────────────────

export interface Holding {
  symbol: string;
  name: string;
  market: Market;
  quantity: number;
  avg_cost: number;
  currency: Currency;
  live_price?: number;
  is_live: boolean;
}

export interface PortfolioData {
  holdings: Holding[];
  total_value: number;
  total_invested: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  currency: Currency;
  last_updated: string;
}


// ── API RESPONSE ──────────────────────────────────────────

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  disclaimer: string;   // Always: "Not financial advice..."
  timestamp: string;
}
