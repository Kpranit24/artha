// =============================================================
// frontend/components/layout/MarketCards.tsx
// PURPOSE:  Summary metric cards showing key market indices
//           Nifty 50 · Sensex · S&P 500 · BTC · ETH · VIX
//
// WHAT IT SHOWS:
//   Each card: Index name | Current value | % change (colored)
//
// DATA:
//   Filters from heatmap bubbles — no extra API call
//
// CLICKING A CARD:
//   Navigates to /ticker/{market}/{symbol} for full chart
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useRouter } from "next/navigation"
import { HeatmapBubble } from "@/types/market"
import { cn } from "@/lib/utils"

interface MarketCardsProps {
  bubbles:   HeatmapBubble[]
  className?: string
}

// These are the symbols we want to show as summary cards
// Edit this list to change which cards appear
const SUMMARY_SYMBOLS = [
  { symbol: "BTC",       label: "Bitcoin",     market: "crypto" },
  { symbol: "ETH",       label: "Ethereum",    market: "crypto" },
  { symbol: "RELIANCE",  label: "Reliance",    market: "india"  },
  { symbol: "TCS",       label: "TCS",         market: "india"  },
  { symbol: "NVDA",      label: "NVIDIA",      market: "us"     },
  { symbol: "AAPL",      label: "Apple",       market: "us"     },
]

export function MarketCards({ bubbles, className }: MarketCardsProps) {
  const router = useRouter()

  // Build a lookup map from bubbles
  const bubbleMap = new Map(bubbles.map(b => [b.symbol, b]))

  return (
    <div className={cn(
      "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2",
      className
    )}>
      {SUMMARY_SYMBOLS.map(({ symbol, label, market }) => {
        const bubble = bubbleMap.get(symbol)

        return (
          <button
            key={symbol}
            onClick={() => router.push(`/ticker/${market}/${symbol}`)}
            className={cn(
              "bg-muted/50 rounded-lg p-3 text-left",
              "hover:bg-muted transition-colors cursor-pointer",
              "border border-transparent hover:border-border"
            )}
          >
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
              {label}
            </div>
            {bubble ? (
              <>
                <div className="text-base font-semibold tabular-nums">
                  {bubble.market === "india" ? "₹" : "$"}
                  {bubble.price.toLocaleString("en-US", {
                    minimumFractionDigits: bubble.price < 10 ? 4 : 2,
                    maximumFractionDigits: bubble.price < 10 ? 4 : 2,
                  })}
                </div>
                <div className={cn(
                  "text-xs mt-0.5 font-medium",
                  bubble.change_pct >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  {bubble.change_pct >= 0 ? "▲" : "▼"}
                  {" "}{Math.abs(bubble.change_pct).toFixed(2)}%
                </div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground">—</div>
            )}
          </button>
        )
      })}
    </div>
  )
}
