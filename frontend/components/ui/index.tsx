// =============================================================
// frontend/components/ui/index.tsx
// PURPOSE:  Small reusable UI components used across all pages
//
// COMPONENTS:
//   LiveBadge      → green "Live" or amber "Delayed" indicator
//   Disclaimer     → "Not financial advice" footer (always visible)
//   TimeframeSelect → 1D / 1W / 1M / YTD / 1Y buttons
//   IndexSelect    → dropdown for Nifty50 / Nasdaq / Crypto / All
//   LoadingState   → centered spinner with message
//   ErrorState     → error message with retry button
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { cn } from "@/lib/utils"
import type { Timeframe } from "@/types/market"


// ── LIVE BADGE ────────────────────────────────────────────

interface LiveBadgeProps {
  isLive:     boolean
  isFetching: boolean
  updatedAt:  number    // timestamp from React Query
}

export function LiveBadge({ isLive, isFetching, updatedAt }: LiveBadgeProps) {
  const age = Math.round((Date.now() - updatedAt) / 1000)

  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className={cn(
        "w-1.5 h-1.5 rounded-full",
        isFetching ? "bg-amber-400 animate-pulse" :
        isLive     ? "bg-green-500 animate-pulse" :
                     "bg-amber-400"
      )} />
      <span>
        {isFetching ? "Updating..." :
         isLive     ? `Live · ${age}s ago` :
                      "Delayed data"}
      </span>
    </div>
  )
}


// ── DISCLAIMER ────────────────────────────────────────────
// Always shown — required for any financial data app

export function Disclaimer({ className }: { className?: string }) {
  return (
    <div className={cn(
      "text-[11px] text-muted-foreground/70 text-center py-4 px-4",
      "border-t border-border/50 mt-4",
      className
    )}>
      Not financial advice. All market data is for informational purposes only.
      Do your own research before making any investment decisions.
      Prices may be delayed. Past performance does not guarantee future results.
    </div>
  )
}


// ── TIMEFRAME SELECT ──────────────────────────────────────
// Synchronized across all charts on the page

const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: "1d",  label: "1D"  },
  { value: "1w",  label: "1W"  },
  { value: "1m",  label: "1M"  },
  { value: "3m",  label: "3M"  },
  { value: "ytd", label: "YTD" },
  { value: "1y",  label: "1Y"  },
]

interface TimeframeSelectProps {
  value:     string
  onChange:  (value: string) => void
  className?: string
}

export function TimeframeSelect({ value, onChange, className }: TimeframeSelectProps) {
  return (
    <div className={cn("flex gap-0.5 bg-muted rounded-lg p-0.5", className)}>
      {TIMEFRAMES.map(tf => (
        <button
          key={tf.value}
          onClick={() => onChange(tf.value)}
          className={cn(
            "px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
            value === tf.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {tf.label}
        </button>
      ))}
    </div>
  )
}


// ── INDEX SELECT ──────────────────────────────────────────

const INDICES = [
  { value: "all",         label: "All markets"  },
  { value: "nifty50",     label: "Nifty 50"     },
  { value: "nifty_it",    label: "Nifty IT"     },
  { value: "nifty_bank",  label: "Nifty Bank"   },
  { value: "nasdaq",      label: "Nasdaq 100"   },
  { value: "sp500",       label: "S&P 500"      },
  { value: "crypto",      label: "Crypto top 20"},
]

interface IndexSelectProps {
  value:     string
  onChange:  (value: string) => void
  className?: string
}

export function IndexSelect({ value, onChange, className }: IndexSelectProps) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className={cn(
        "text-xs bg-muted border-0 rounded-lg px-3 py-1.5",
        "text-foreground cursor-pointer",
        "focus:outline-none focus:ring-1 focus:ring-ring",
        className
      )}
    >
      {INDICES.map(idx => (
        <option key={idx.value} value={idx.value}>
          {idx.label}
        </option>
      ))}
    </select>
  )
}


// ── LOADING STATE ─────────────────────────────────────────

interface LoadingStateProps {
  message?: string
  className?: string
}

export function LoadingState({
  message = "Loading...",
  className
}: LoadingStateProps) {
  return (
    <div className={cn(
      "min-h-[400px] flex flex-col items-center justify-center gap-3",
      className
    )}>
      {/* Spinner */}
      <div className="w-6 h-6 border-2 border-muted border-t-foreground rounded-full animate-spin" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  )
}


// ── ERROR STATE ───────────────────────────────────────────

interface ErrorStateProps {
  message:   string
  retry?:    () => void
  className?: string
}

export function ErrorState({ message, retry, className }: ErrorStateProps) {
  return (
    <div className={cn(
      "min-h-[400px] flex flex-col items-center justify-center gap-4",
      className
    )}>
      <div className="text-4xl">⚠</div>
      <div className="text-center">
        <p className="text-sm font-medium text-foreground mb-1">
          Something went wrong
        </p>
        <p className="text-xs text-muted-foreground max-w-sm">
          {message}
        </p>
      </div>
      {retry && (
        <button
          onClick={retry}
          className="text-xs px-4 py-2 bg-muted hover:bg-muted/80 rounded-lg transition-colors"
        >
          Try again
        </button>
      )}
      <Disclaimer />
    </div>
  )
}
