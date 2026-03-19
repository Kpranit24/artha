// =============================================================
// frontend/components/layout/TickerTape.tsx
// PURPOSE:  Scrolling ticker tape showing live prices at top
//
// WHAT IT SHOWS:
//   Scrolling row of: SYMBOL  $PRICE  +/-CHANGE%
//   Green for positive, red for negative
//   Pauses on hover so users can read
//
// DATA:
//   Receives bubbles from parent (already fetched)
//   No additional API calls — uses heatmap data
//
// ANIMATION:
//   CSS animation — no JavaScript, very performant
//   Duplicates the items so scroll loops seamlessly
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { HeatmapBubble } from "@/types/market"
import { cn } from "@/lib/utils"

interface TickerTapeProps {
  bubbles: HeatmapBubble[]
  isLive:  boolean
  className?: string
}

export function TickerTape({ bubbles, isLive, className }: TickerTapeProps) {
  if (!bubbles.length) return null

  // Build ticker items
  const items = bubbles.map(b => ({
    symbol:    b.symbol,
    price:     b.price,
    change:    b.change_pct,
    currency:  b.market === "india" ? "INR" : "USD",
    isUp:      b.change_pct >= 0,
  }))

  // Duplicate for seamless loop
  const allItems = [...items, ...items]

  return (
    <div className={cn(
      "overflow-hidden border-b border-border bg-background",
      className
    )}>
      <div className="flex items-center gap-0">
        {/* Live indicator dot */}
        <div className="flex-shrink-0 px-3 flex items-center gap-1.5 border-r border-border h-8">
          <span className={cn(
            "w-1.5 h-1.5 rounded-full",
            isLive ? "bg-green-500 animate-pulse" : "bg-amber-500"
          )} />
          <span className="text-[10px] text-muted-foreground font-medium">
            {isLive ? "LIVE" : "DELAYED"}
          </span>
        </div>

        {/* Scrolling tape */}
        <div
          className="overflow-hidden flex-1"
          style={{ maskImage: "linear-gradient(to right, transparent, black 3%, black 97%, transparent)" }}
        >
          <div
            className="flex gap-6 whitespace-nowrap animate-ticker hover:[animation-play-state:paused]"
            style={{
              // CSS animation for smooth infinite scroll
              animation: "ticker 40s linear infinite",
            }}
          >
            {allItems.map((item, i) => (
              <span key={i} className="inline-flex items-center gap-2 text-xs py-1.5">
                <span className="font-semibold text-foreground">{item.symbol}</span>
                <span className="text-muted-foreground">
                  {item.currency === "INR" ? "₹" : "$"}
                  {item.price.toLocaleString("en-US", {
                    minimumFractionDigits: item.price < 10 ? 4 : 2,
                    maximumFractionDigits: item.price < 10 ? 4 : 2,
                  })}
                </span>
                <span className={item.isUp ? "text-green-600" : "text-red-600"}>
                  {item.isUp ? "▲" : "▼"}
                  {Math.abs(item.change).toFixed(2)}%
                </span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Keyframe animation in a style tag */}
      <style jsx>{`
        @keyframes ticker {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  )
}
