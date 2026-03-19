// =============================================================
// frontend/components/layout/TopMovers.tsx
// PURPOSE:  Right sidebar showing top gainers and losers
//
// WHAT IT SHOWS:
//   Two tabs: Gainers | Losers
//   Each row: Symbol | Name | Price | % change pill
//
// TABS:
//   Gainers → biggest positive movers
//   Losers  → biggest negative movers
//   Both sorted by absolute % change
//
// CLICKING A ROW:
//   Navigates to full ticker page
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"

interface Mover {
  symbol:    string
  name:      string
  price:     number
  change_1d: number
  market:    string
  currency:  string
  is_live:   boolean
}

interface TopMoversProps {
  gainers: Mover[]
  losers:  Mover[]
  className?: string
}

export function TopMovers({ gainers, losers, className }: TopMoversProps) {
  const [tab,    setTab]    = useState<"gainers" | "losers">("gainers")
  const router = useRouter()

  const items = tab === "gainers" ? gainers : losers

  return (
    <div className={cn("bg-card border rounded-xl p-4 flex flex-col", className)}>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-3">
        <button
          onClick={() => setTab("gainers")}
          className={cn(
            "flex-1 text-xs py-1.5 rounded-md font-medium transition-colors",
            tab === "gainers"
              ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
              : "text-muted-foreground hover:bg-muted"
          )}
        >
          Top gainers
        </button>
        <button
          onClick={() => setTab("losers")}
          className={cn(
            "flex-1 text-xs py-1.5 rounded-md font-medium transition-colors",
            tab === "losers"
              ? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400"
              : "text-muted-foreground hover:bg-muted"
          )}
        >
          Top losers
        </button>
      </div>

      {/* Mover rows */}
      <div className="flex flex-col divide-y divide-border">
        {items.length === 0 && (
          <div className="text-xs text-muted-foreground py-4 text-center">
            No data available
          </div>
        )}
        {items.map((mover) => (
          <button
            key={mover.symbol}
            onClick={() => router.push(`/ticker/${mover.market}/${mover.symbol}`)}
            className="flex items-center justify-between py-2.5 hover:bg-muted/50 -mx-1 px-1 rounded transition-colors text-left"
          >
            {/* Symbol + name */}
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold">{mover.symbol}</span>
                {/* Live indicator */}
                {mover.is_live && (
                  <span className="w-1 h-1 rounded-full bg-green-500" />
                )}
              </div>
              <div className="text-[11px] text-muted-foreground truncate max-w-[120px]">
                {mover.name}
              </div>
            </div>

            {/* Price + change */}
            <div className="text-right">
              <div className="text-sm font-medium tabular-nums">
                {mover.currency === "INR" ? "₹" : "$"}
                {mover.price.toLocaleString("en-US", {
                  minimumFractionDigits: mover.price < 10 ? 4 : 2,
                  maximumFractionDigits: mover.price < 10 ? 4 : 2,
                })}
              </div>
              <span className={cn(
                "text-[11px] font-medium px-1.5 py-0.5 rounded",
                mover.change_1d >= 0
                  ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
                  : "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400"
              )}>
                {mover.change_1d >= 0 ? "+" : ""}
                {mover.change_1d.toFixed(2)}%
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
