// =============================================================
// frontend/app/screener/page.tsx
// PURPOSE:  Stock screener page — filter and rank tickers
//
// FEATURES:
//   - 6 preset filters: gainers, losers, volume, cap, ATH, 7d
//   - Market filter: All / India / US / Crypto
//   - Live data refreshes every 30s
//   - Click any row → full ticker page
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { api, REFETCH_INTERVAL_MS } from "@/lib/api"
import { Disclaimer, LoadingState, ErrorState, TimeframeSelect } from "@/components/ui"
import { cn, formatLargeNumber } from "@/lib/utils"
import type { TickerData } from "@/types/market"


const FILTERS = [
  { value: "gainers", label: "Top gainers",   desc: "Biggest 24h risers"     },
  { value: "losers",  label: "Top losers",    desc: "Biggest 24h fallers"    },
  { value: "volume",  label: "Top volume",    desc: "Highest trading volume" },
  { value: "cap",     label: "Largest cap",   desc: "By market cap"          },
  { value: "ath",     label: "Near ATH",      desc: "Closest to all-time high"},
  { value: "week",    label: "Best 7-day",    desc: "Top weekly performers"  },
]

const MARKETS = [
  { value: "all",    label: "All"    },
  { value: "india",  label: "India"  },
  { value: "us",     label: "US"     },
  { value: "crypto", label: "Crypto" },
]


export default function ScreenerPage() {
  const router   = useRouter()
  const [filter,    setFilter]    = useState("gainers")
  const [market,    setMarket]    = useState("all")
  const [timeframe, setTimeframe] = useState("1d")

  const { data, isLoading, isError, error, dataUpdatedAt } = useQuery({
    queryKey:        ["screener", market, filter, timeframe],
    queryFn:         () => api.screener.get({ market, filter, timeframe, limit: 20 }),
    refetchInterval: REFETCH_INTERVAL_MS * 2,
  })

  if (isLoading) return <LoadingState message="Loading screener..." />
  if (isError)   return <ErrorState message={error instanceof Error ? error.message : "Failed"} />

  const tickers: TickerData[] = data || []
  const activeFilter = FILTERS.find(f => f.value === filter)

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-4">

      {/* Filter presets */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mb-4">
        {FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "rounded-xl p-3 text-left border transition-all",
              filter === f.value
                ? "border-foreground/30 bg-muted"
                : "border-border bg-card hover:bg-muted/50"
            )}
          >
            <div className="text-xs font-semibold mb-0.5">{f.label}</div>
            <div className="text-[10px] text-muted-foreground">{f.desc}</div>
          </button>
        ))}
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{activeFilter?.label}</span>
          <span className="text-xs text-muted-foreground">— {tickers.length} results</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Market filter */}
          <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
            {MARKETS.map(m => (
              <button
                key={m.value}
                onClick={() => setMarket(m.value)}
                className={cn(
                  "px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
                  market === m.value
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
          <TimeframeSelect value={timeframe} onChange={setTimeframe} />
        </div>
      </div>

      {/* Results table */}
      <div className="bg-card border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                {["#", "Ticker", "Market", "Price", "24h %", "7d %", "Mkt cap", "Volume", "ATH %", "Signal"].map(h => (
                  <th key={h} className="text-left text-[11px] text-muted-foreground font-medium px-3 py-2.5 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tickers.length === 0 && (
                <tr>
                  <td colSpan={10} className="text-center py-8 text-muted-foreground text-sm">
                    No results for this filter.
                  </td>
                </tr>
              )}
              {tickers.map((ticker, i) => {
                const isUp1d = (ticker.change_1d ?? 0) >= 0
                const isUp7d = (ticker.change_7d ?? 0) >= 0
                const signal = (ticker.change_1d ?? 0) > 3 ? "Strong buy"
                             : (ticker.change_1d ?? 0) > 0 ? "Bullish"
                             : (ticker.change_1d ?? 0) > -3 ? "Bearish"
                             : "Strong sell"
                const signalColor = signal.includes("buy") || signal === "Bullish"
                  ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
                  : "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400"

                return (
                  <tr
                    key={ticker.symbol}
                    onClick={() => router.push(`/ticker/${ticker.market}/${ticker.symbol}`)}
                    className="border-b border-border/50 hover:bg-muted/40 cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-2.5 text-muted-foreground">{i + 1}</td>
                    <td className="px-3 py-2.5">
                      <div className="font-semibold">{ticker.symbol}</div>
                      <div className="text-[10px] text-muted-foreground truncate max-w-[100px]">{ticker.name}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded font-medium",
                        ticker.market === "india"  ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400" :
                        ticker.market === "us"     ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400" :
                                                     "bg-orange-50 text-orange-700 dark:bg-orange-950 dark:text-orange-400"
                      )}>
                        {ticker.market.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 tabular-nums font-medium">
                      {ticker.currency === "INR" ? "₹" : "$"}
                      {ticker.price.toLocaleString("en-US", {
                        minimumFractionDigits: ticker.price < 10 ? 4 : 2,
                        maximumFractionDigits: ticker.price < 10 ? 4 : 2,
                      })}
                    </td>
                    <td className={cn("px-3 py-2.5 tabular-nums font-medium", isUp1d ? "text-green-600" : "text-red-600")}>
                      {ticker.change_1d != null ? (isUp1d ? "+" : "") + ticker.change_1d.toFixed(2) + "%" : "—"}
                    </td>
                    <td className={cn("px-3 py-2.5 tabular-nums", isUp7d ? "text-green-600" : "text-red-600")}>
                      {ticker.change_7d != null ? (isUp7d ? "+" : "") + ticker.change_7d.toFixed(2) + "%" : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground tabular-nums">
                      {ticker.market_cap ? formatLargeNumber(ticker.market_cap) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground tabular-nums">
                      {ticker.volume_24h ? formatLargeNumber(ticker.volume_24h) : "—"}
                    </td>
                    <td className={cn("px-3 py-2.5 tabular-nums",
                      (ticker.ath_change_pct ?? -100) > -5 ? "text-green-600" : "text-muted-foreground"
                    )}>
                      {ticker.ath_change_pct != null ? ticker.ath_change_pct.toFixed(1) + "%" : "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium", signalColor)}>
                        {signal}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <Disclaimer />
    </div>
  )
}
