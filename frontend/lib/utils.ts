// =============================================================
// frontend/lib/utils.ts
// PURPOSE:  Shared utility functions used across the frontend
//
// LAST UPDATED: March 2026
// =============================================================

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"


// ── TAILWIND CLASS MERGER ─────────────────────────────────
// Standard shadcn/ui pattern
// Merges Tailwind classes without conflicts

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}


// ── NUMBER FORMATTERS ─────────────────────────────────────

export function formatPrice(price: number, currency: "USD" | "INR"): string {
  const symbol = currency === "INR" ? "₹" : "$"
  if (price >= 1000) {
    return symbol + price.toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })
  }
  return symbol + price.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: price < 1 ? 4 : 2,
  })
}

export function formatChange(change: number): string {
  const prefix = change >= 0 ? "+" : ""
  return `${prefix}${change.toFixed(2)}%`
}

export function formatLargeNumber(n: number): string {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6)  return `$${(n / 1e6).toFixed(2)}M`
  return `$${n.toLocaleString()}`
}

export function formatVolume(v: number): string {
  if (v >= 1e9)  return `${(v / 1e9).toFixed(1)}B`
  if (v >= 1e6)  return `${(v / 1e6).toFixed(1)}M`
  if (v >= 1e3)  return `${(v / 1e3).toFixed(1)}K`
  return v.toString()
}


// ── DATE HELPERS ──────────────────────────────────────────

export function timeAgo(timestamp: number): string {
  const seconds = Math.round((Date.now() - timestamp) / 1000)
  if (seconds < 60)  return `${seconds}s ago`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`
  return `${Math.round(seconds / 3600)}h ago`
}

export function formatIST(isoString: string): string {
  return new Date(isoString).toLocaleString("en-IN", {
    timeZone:    "Asia/Kolkata",
    hour:        "2-digit",
    minute:      "2-digit",
    hour12:      true,
    day:         "numeric",
    month:       "short",
  }) + " IST"
}


// ── MARKET HELPERS ────────────────────────────────────────

export function getMarketColor(market: string): string {
  return {
    india:  "#185FA5",
    us:     "#1D9E75",
    crypto: "#D85A30",
  }[market] ?? "#888"
}

export function isMarketOpen(market: string): boolean {
  const now = new Date()
  const ist = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }))
  const et  = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }))
  const day = ist.getDay()

  if (market === "crypto") return true // Crypto never closes

  if (market === "india") {
    // NSE: Mon-Fri 9:15am - 3:30pm IST
    if (day === 0 || day === 6) return false
    const h = ist.getHours(), m = ist.getMinutes()
    return (h > 9 || (h === 9 && m >= 15)) && (h < 15 || (h === 15 && m <= 30))
  }

  if (market === "us") {
    // NYSE: Mon-Fri 9:30am - 4:00pm ET
    if (day === 0 || day === 6) return false
    const h = et.getHours(), m = et.getMinutes()
    return (h > 9 || (h === 9 && m >= 30)) && h < 16
  }

  return false
}
