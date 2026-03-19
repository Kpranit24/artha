// =============================================================
// frontend/app/macro/page.tsx
// PURPOSE:  Macro indicators page — rates, fear/greed, events
//
// WHAT IT SHOWS:
//   - Key macro indicators (RBI rate, Fed rate, CPI, yields)
//   - Crypto fear & greed index (live from alternative.me)
//   - Upcoming macro events calendar
//   - Price alerts management
//
// DATA SOURCES:
//   Fear & greed: live from alternative.me (free)
//   Macro indicators: static reference data (updated manually)
//   Events: hardcoded calendar (TODO: wire to economic calendar API)
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState, useEffect } from "react"
import { Disclaimer } from "@/components/ui"
import { cn } from "@/lib/utils"


// Static macro data — update monthly
// TODO: Wire to FRED API (free) for live macro data
const MACRO_INDICATORS = [
  { label: "RBI repo rate",        value: "6.25%", note: "On hold — Apr 2026 review",   region: "India" },
  { label: "India CPI (Feb 2026)", value: "4.3%",  note: "Within 2-6% RBI band",        region: "India" },
  { label: "India 10Y yield",      value: "6.88%", note: "Stable",                       region: "India" },
  { label: "India VIX",            value: "13.82", note: "Low volatility zone",          region: "India" },
  { label: "USD / INR",            value: "86.42", note: "Strong dollar",                region: "India" },
  { label: "Fed funds rate",       value: "4.75%", note: "Cuts expected Q3 2026",        region: "US"    },
  { label: "US CPI (Feb 2026)",    value: "3.1%",  note: "Above 2% target",             region: "US"    },
  { label: "US 10Y yield",         value: "4.22%", note: "Elevated",                    region: "US"    },
  { label: "DXY dollar index",     value: "104.6", note: "Strong vs EM currencies",     region: "US"    },
  { label: "Gold (spot)",          value: "$2,178",note: "Near 6-month high",            region: "Global"},
  { label: "Brent crude",          value: "$82.1", note: "OPEC+ production hold",       region: "Global"},
  { label: "BTC dominance",        value: "52.4%", note: "Altcoin season unlikely",     region: "Crypto"},
]

const UPCOMING_EVENTS = [
  { date: "Mar 20", event: "TCS quarterly earnings",           impact: "high",   region: "India"  },
  { date: "Mar 21", event: "NVIDIA Q1 2026 earnings",          impact: "high",   region: "US"     },
  { date: "Mar 22", event: "India trade balance (Feb)",        impact: "medium", region: "India"  },
  { date: "Mar 23", event: "Nifty monthly F&O expiry",        impact: "high",   region: "India"  },
  { date: "Mar 25", event: "US PCE inflation print",           impact: "high",   region: "US"     },
  { date: "Mar 26", event: "RBI MPC minutes release",          impact: "medium", region: "India"  },
  { date: "Apr 02", event: "RBI Monetary Policy Committee",   impact: "high",   region: "India"  },
  { date: "Apr 10", event: "US CPI March reading",             impact: "high",   region: "US"     },
]

interface FearGreedData {
  value:                number
  value_classification: string
  timestamp:            string
}


export default function MacroPage() {
  const [regionFilter, setRegionFilter] = useState("All")
  const [fearGreed, setFearGreed]       = useState<FearGreedData | null>(null)
  const [fgHistory, setFgHistory]       = useState<FearGreedData[]>([])
  const [fgLoading, setFgLoading]       = useState(true)

  // Fetch fear & greed index on mount
  useEffect(() => {
    fetch("https://api.alternative.me/fng/?limit=7")
      .then(r => r.json())
      .then(data => {
        const items = data?.data || []
        setFearGreed(items[0] || null)
        setFgHistory(items.slice(0, 7).reverse())
      })
      .catch(() => {})
      .finally(() => setFgLoading(false))
  }, [])

  const filteredIndicators = MACRO_INDICATORS.filter(
    m => regionFilter === "All" || m.region === regionFilter
  )
  const filteredEvents = UPCOMING_EVENTS.filter(
    e => regionFilter === "All" || e.region === regionFilter || e.region === "Global"
  )

  // Fear & greed color
  const fgValue = parseInt(fearGreed?.value?.toString() ?? "50")
  const fgColor = fgValue >= 60 ? "#3B6D11" : fgValue >= 40 ? "#BA7517" : "#A32D2D"
  const fgLabel = fearGreed?.value_classification ?? "Neutral"

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-4">

      {/* Region filter */}
      <div className="flex items-center gap-1 mb-4">
        {["All", "India", "US", "Crypto", "Global"].map(r => (
          <button
            key={r}
            onClick={() => setRegionFilter(r)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
              regionFilter === r
                ? "bg-foreground text-background"
                : "bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            {r}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">

        {/* Fear & Greed Index */}
        <div className="bg-card border rounded-xl p-4">
          <div className="text-xs font-medium text-muted-foreground mb-3">
            Crypto fear &amp; greed — live
          </div>
          {fgLoading ? (
            <div className="text-sm text-muted-foreground">Loading...</div>
          ) : fearGreed ? (
            <>
              <div className="flex items-baseline gap-3 mb-3">
                <span className="text-5xl font-bold tabular-nums" style={{ color: fgColor }}>
                  {fgValue}
                </span>
                <span className="text-lg font-semibold" style={{ color: fgColor }}>
                  {fgLabel}
                </span>
              </div>
              {/* Gauge bar */}
              <div
                className="h-2.5 rounded-full mb-1 overflow-hidden"
                style={{ background: "linear-gradient(to right, #A32D2D, #D85A30, #BA7517, #3B6D11)" }}
              >
                <div
                  className="h-full w-1 bg-white rounded-full shadow-sm transition-all"
                  style={{ marginLeft: `${Math.max(0, Math.min(98, fgValue - 1))}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted-foreground mb-3">
                <span>Extreme fear</span>
                <span>Neutral</span>
                <span>Extreme greed</span>
              </div>
              {/* 7-day history */}
              {fgHistory.length > 0 && (
                <div>
                  <div className="text-[10px] text-muted-foreground mb-1.5">7-day history</div>
                  <div className="flex gap-1">
                    {fgHistory.map((d, i) => {
                      const v = parseInt(d.value.toString())
                      const c = v >= 60 ? "#3B6D11" : v >= 40 ? "#BA7517" : "#A32D2D"
                      const day = new Date(parseInt(d.timestamp) * 1000)
                        .toLocaleDateString("en", { weekday: "short" })
                      return (
                        <div key={i} className="flex-1 text-center">
                          <div className="text-xs font-semibold tabular-nums" style={{ color: c }}>{v}</div>
                          <div className="text-[9px] text-muted-foreground">{day}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-sm text-muted-foreground">
              Fear &amp; greed index unavailable. API may be rate limited.
            </div>
          )}
        </div>

        {/* Key macro indicators */}
        <div className="bg-card border rounded-xl p-4 lg:col-span-2">
          <div className="text-xs font-medium text-muted-foreground mb-3">
            Key macro indicators
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-0">
            {filteredIndicators.map(ind => (
              <div
                key={ind.label}
                className="flex items-center justify-between py-2 border-b border-border/50 last:border-0 gap-3"
              >
                <div>
                  <div className="text-xs font-medium">{ind.label}</div>
                  <div className="text-[10px] text-muted-foreground">{ind.note}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-sm font-semibold tabular-nums">{ind.value}</div>
                  <div className={cn(
                    "text-[10px] px-1.5 py-0.5 rounded font-medium",
                    ind.region === "India"  ? "text-blue-600" :
                    ind.region === "US"     ? "text-green-600" :
                    ind.region === "Crypto" ? "text-orange-600" :
                                              "text-muted-foreground"
                  )}>
                    {ind.region}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Upcoming events */}
      <div className="bg-card border rounded-xl p-4 mb-4">
        <div className="text-xs font-medium text-muted-foreground mb-3">
          Upcoming macro events
        </div>
        <div className="divide-y divide-border/50">
          {filteredEvents.map((ev, i) => (
            <div key={i} className="flex items-center justify-between py-2.5 gap-3">
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-12 flex-shrink-0 tabular-nums">
                  {ev.date}
                </span>
                <span className="text-xs">{ev.event}</span>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded font-medium",
                  ev.region === "India"  ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400" :
                  ev.region === "US"     ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400" :
                                           "bg-muted text-muted-foreground"
                )}>
                  {ev.region}
                </span>
                <span className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded font-medium",
                  ev.impact === "high"
                    ? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400"
                    : "bg-muted text-muted-foreground"
                )}>
                  {ev.impact}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Disclaimer />
    </div>
  )
}
