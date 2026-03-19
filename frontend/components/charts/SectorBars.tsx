// =============================================================
// frontend/components/charts/SectorBars.tsx
// PURPOSE:  Horizontal bar chart showing sector performance
//           One bar per ticker, colored green/red by % change
//
// WHAT IT SHOWS:
//   Top 8 tickers from the given bubbles array
//   Sorted by % change (best at top)
//   Bar width proportional to % change
//
// DATA:
//   Receives filtered bubbles from parent (no extra API calls)
//   Parent filters by market: india / us / crypto
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useRouter } from "next/navigation"
import { HeatmapBubble } from "@/types/market"
import { cn } from "@/lib/utils"

interface SectorBarsProps {
  bubbles:   HeatmapBubble[]
  height?:   number
  maxItems?: number
  className?: string
}

export function SectorBars({
  bubbles,
  height = 200,
  maxItems = 8,
  className,
}: SectorBarsProps) {
  const router = useRouter()

  // Sort by absolute % change, take top N
  const sorted = [...bubbles]
    .sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct))
    .slice(0, maxItems)

  if (!sorted.length) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
        No data
      </div>
    )
  }

  // Find max absolute change for bar scaling
  const maxChange = Math.max(...sorted.map(b => Math.abs(b.change_pct)), 1)

  return (
    <div
      className={cn("flex flex-col gap-1.5", className)}
      style={{ minHeight: height }}
    >
      {sorted.map(bubble => {
        const isUp       = bubble.change_pct >= 0
        const barWidth   = Math.abs(bubble.change_pct) / maxChange * 100

        return (
          <button
            key={bubble.symbol}
            onClick={() => router.push(`/ticker/${bubble.market}/${bubble.symbol}`)}
            className="flex items-center gap-2 hover:bg-muted/50 -mx-1 px-1 py-0.5 rounded transition-colors w-full text-left"
          >
            {/* Symbol label */}
            <span className="text-[11px] font-medium w-16 flex-shrink-0 truncate">
              {bubble.symbol}
            </span>

            {/* Bar */}
            <div className="flex-1 h-4 bg-muted rounded-sm overflow-hidden relative">
              <div
                className={cn(
                  "h-full rounded-sm transition-all duration-500",
                  isUp
                    ? "bg-green-100 dark:bg-green-950"
                    : "bg-red-100 dark:bg-red-950"
                )}
                style={{ width: `${barWidth}%` }}
              />
              {/* Bar fill overlay */}
              <div
                className={cn(
                  "absolute inset-y-0 left-0 rounded-sm opacity-40",
                  isUp ? "bg-green-500" : "bg-red-500"
                )}
                style={{ width: `${barWidth * 0.6}%` }}
              />
            </div>

            {/* % change label */}
            <span className={cn(
              "text-[11px] font-medium w-12 text-right flex-shrink-0",
              isUp ? "text-green-600" : "text-red-600"
            )}>
              {isUp ? "+" : ""}{bubble.change_pct.toFixed(2)}%
            </span>
          </button>
        )
      })}
    </div>
  )
}
