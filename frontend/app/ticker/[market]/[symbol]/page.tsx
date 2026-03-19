// =============================================================
// frontend/app/ticker/[market]/[symbol]/page.tsx
// PURPOSE:  Full ticker detail page — price, chart, AI insight
//
// URL: /ticker/crypto/BTC
//      /ticker/india/TCS
//      /ticker/us/NVDA
//
// WHAT IT SHOWS:
//   - Live price + % change + key stats
//   - Candlestick OHLCV chart (Plotly)
//   - AI insight: headline, bull/bear case, key drivers
//   - Link back to screener/heatmap
//
// DATA:
//   GET /api/ticker/{symbol}?market={market}&timeframe={tf}&insight=true
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState }          from "react"
import { useQuery }          from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { api, REFETCH_INTERVAL_MS } from "@/lib/api"
import { Disclaimer, LoadingState, ErrorState, TimeframeSelect } from "@/components/ui"
import { CandlestickChart }  from "@/components/charts/CandlestickChart"
import { cn, formatLargeNumber } from "@/lib/utils"


export default function TickerPage() {
  const params    = useParams()
  const router    = useRouter()
  const symbol    = (params.symbol as string)?.toUpperCase()
  const market    = params.market as string
  const [timeframe, setTimeframe] = useState("1m")

  const { data, isLoading, isError, error } = useQuery({
    queryKey:        ["ticker", symbol, market, timeframe],
    queryFn:         () => api.ticker.get({ symbol, market, timeframe, insight: true }),
    refetchInterval: REFETCH_INTERVAL_MS * 2,
  })

  if (isLoading) return <LoadingState message={`Loading ${symbol}...`} />
  if (isError)   return <ErrorState message={error instanceof Error ? error.message : "Failed"} />
  if (!data)     return null

  const { ticker, ohlcv, insight } = data
  const isUp = (ticker.change_1d ?? 0) >= 0
  const currency = ticker.currency === "INR" ? "₹" : "$"

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-4">

      {/* Back button */}
      <button
        onClick={() => router.back()}
        className="text-xs text-muted-foreground hover:text-foreground mb-4 flex items-center gap-1"
      >
        ← Back
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold">{symbol}</h1>
            <span className={cn(
              "text-xs px-2 py-0.5 rounded font-medium",
              market === "india"  ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400" :
              market === "us"     ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400" :
                                    "bg-orange-50 text-orange-700 dark:bg-orange-950 dark:text-orange-400"
            )}>
              {market.toUpperCase()}
            </span>
            {!ticker.is_live && (
              <span className="text-[10px] bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-400 px-1.5 py-0.5 rounded">
                Delayed
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">{ticker.name}</p>
        </div>
        <TimeframeSelect value={timeframe} onChange={setTimeframe} />
      </div>

      {/* Price + stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div className="bg-muted/50 rounded-xl p-3">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Price</div>
          <div className="text-2xl font-bold tabular-nums">
            {currency}{ticker.price.toLocaleString("en-US", {
              minimumFractionDigits: ticker.price < 10 ? 4 : 2,
              maximumFractionDigits: ticker.price < 10 ? 4 : 2,
            })}
          </div>
          <div className={cn("text-sm font-medium mt-0.5", isUp ? "text-green-600" : "text-red-600")}>
            {isUp ? "▲" : "▼"} {Math.abs(ticker.change_1d ?? 0).toFixed(2)}% (24h)
          </div>
        </div>

        {[
          { label: "Market cap",  value: ticker.market_cap    ? formatLargeNumber(ticker.market_cap)    : "—" },
          { label: "Volume 24h",  value: ticker.volume_24h    ? formatLargeNumber(ticker.volume_24h)    : "—" },
          { label: "7d change",   value: ticker.change_7d != null ? (ticker.change_7d >= 0 ? "+" : "") + ticker.change_7d.toFixed(2) + "%" : "—", color: (ticker.change_7d ?? 0) >= 0 ? "text-green-600" : "text-red-600" },
        ].map(stat => (
          <div key={stat.label} className="bg-muted/50 rounded-xl p-3">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{stat.label}</div>
            <div className={cn("text-lg font-semibold tabular-nums", stat.color)}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-card border rounded-xl p-4 mb-4">
        <div className="text-xs font-medium text-muted-foreground mb-3">
          {symbol} — {timeframe} chart
        </div>
        {ohlcv && ohlcv.length > 0 ? (
          <CandlestickChart
            data={ohlcv}
            symbol={symbol}
            currency={ticker.currency}
            height={300}
          />
        ) : (
          <div className="h-[300px] flex items-center justify-center text-sm text-muted-foreground">
            No chart data available for this timeframe
          </div>
        )}
      </div>

      {/* AI Insight */}
      {insight && (
        <div className="bg-card border rounded-xl p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-medium text-muted-foreground">AI insight</div>
            <span className={cn(
              "text-[10px] px-2 py-0.5 rounded font-medium",
              insight.sentiment === "bullish" ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400" :
              insight.sentiment === "bearish" ? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400" :
                                                "bg-muted text-muted-foreground"
            )}>
              {insight.sentiment} · {insight.confidence} confidence
            </span>
          </div>

          <p className="text-sm font-medium mb-2">{insight.headline}</p>
          <p className="text-xs text-muted-foreground mb-3 leading-relaxed">{insight.summary}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <div className="bg-green-50 dark:bg-green-950 rounded-lg p-3">
              <div className="text-[10px] font-medium text-green-700 dark:text-green-400 mb-1">Bull case</div>
              <p className="text-xs text-green-800 dark:text-green-300">{insight.bull_case}</p>
            </div>
            <div className="bg-red-50 dark:bg-red-950 rounded-lg p-3">
              <div className="text-[10px] font-medium text-red-700 dark:text-red-400 mb-1">Bear case</div>
              <p className="text-xs text-red-800 dark:text-red-300">{insight.bear_case}</p>
            </div>
          </div>

          {insight.key_drivers.length > 0 && (
            <div>
              <div className="text-[10px] text-muted-foreground mb-1.5">Key drivers</div>
              <div className="flex flex-wrap gap-1">
                {insight.key_drivers.map((d, i) => (
                  <span key={i} className="text-[10px] bg-muted px-2 py-0.5 rounded">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}

          <p className="text-[10px] text-muted-foreground/60 mt-3">{insight.disclaimer}</p>
        </div>
      )}

      <Disclaimer />
    </div>
  )
}
