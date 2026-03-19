// =============================================================
// frontend/app/dashboard/page.tsx
// PURPOSE:  Main dashboard page — entry point for the app
//
// WHAT THIS PAGE SHOWS:
//   1. Live ticker tape (top)
//   2. Market summary cards (Nifty, S&P, BTC, ETH, Gold, VIX)
//   3. Bubble heatmap (center — the main feature)
//   4. Top movers (right panel — India / US / Crypto)
//   5. Sector performance bars (bottom)
//
// DATA FLOW:
//   useQuery (React Query) → api.heatmap.get() → FastAPI → Redis → CoinGecko/yfinance
//
// AUTO-REFRESH:
//   React Query polls every 15 seconds (REFETCH_INTERVAL_MS)
//   Shows "Live" badge when data is fresh, "Delayed" when stale
//
// TABS:
//   Markets | Heatmap | Portfolio | Screener | Earnings | Macro
//   Each tab is a separate page in /app/{tab}/page.tsx
//
// AI AGENT MONITORS:
//   frontend_agent → watches bundle size, render errors, load time
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { api, REFETCH_INTERVAL_MS } from "@/lib/api"
import { HeatmapChart }    from "@/components/charts/HeatmapChart"
import { TickerTape }      from "@/components/layout/TickerTape"
import { MarketCards }     from "@/components/layout/MarketCards"
import { TopMovers }       from "@/components/layout/TopMovers"
import { SectorBars }      from "@/components/charts/SectorBars"
import { TimeframeSelect } from "@/components/ui/TimeframeSelect"
import { IndexSelect }     from "@/components/ui/IndexSelect"
import { Disclaimer }      from "@/components/ui/Disclaimer"
import { LoadingState }    from "@/components/ui/LoadingState"
import { ErrorState }      from "@/components/ui/ErrorState"
import { LiveBadge }       from "@/components/ui/LiveBadge"
import type { Timeframe }  from "@/types/market"


export default function DashboardPage() {
  // ── STATE ──────────────────────────────────────────────
  // These control which data the heatmap shows
  // Changing them triggers a new API call via React Query
  const [timeframe, setTimeframe] = useState<Timeframe>("1d")
  const [index,     setIndex]     = useState("all")


  // ── DATA FETCHING ──────────────────────────────────────
  // React Query handles:
  //   - Initial fetch on page load
  //   - Auto-refetch every 15 seconds
  //   - Caching between tab switches
  //   - Loading and error states
  const {
    data,
    isLoading,
    isError,
    error,
    dataUpdatedAt,
    isFetching,
  } = useQuery({
    queryKey:      ["heatmap", index, timeframe],  // Re-fetches when these change
    queryFn:       () => api.heatmap.get({ index, timeframe }),
    refetchInterval: REFETCH_INTERVAL_MS,          // 15 seconds
    staleTime:     REFETCH_INTERVAL_MS,            // Don't refetch if < 15s old
    retry:         3,                              // Retry 3x on failure

    // NOTE: If heatmap data already in cache from another tab,
    // React Query shows it immediately while fetching fresh data.
    // This is why the dashboard feels instant.
  })


  // ── RENDER ─────────────────────────────────────────────

  if (isLoading) {
    return <LoadingState message="Loading market data..." />
  }

  if (isError) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Failed to load market data"}
        retry={() => window.location.reload()}
      />
    )
  }

  return (
    <div className="min-h-screen bg-background">

      {/* ── TICKER TAPE ───────────────────────────────── */}
      {/* Scrolling live prices across the top */}
      {data && (
        <TickerTape
          bubbles={data.bubbles}
          isLive={data.is_live}
        />
      )}

      {/* ── MAIN CONTENT ──────────────────────────────── */}
      <main className="max-w-[1400px] mx-auto px-4 py-4">

        {/* ── HEADER ROW ──────────────────────────────── */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold">Markets</h1>
            {/* Shows "Live" with green dot, or "Delayed" with amber dot */}
            <LiveBadge
              isLive={data?.is_live ?? false}
              isFetching={isFetching}
              updatedAt={dataUpdatedAt}
            />
          </div>

          <div className="flex items-center gap-2">
            {/* Index selector — Nifty50 / Nasdaq / Crypto / All */}
            <IndexSelect
              value={index}
              onChange={setIndex}
            />
            {/* Timeframe — 1D / 1W / 1M / YTD */}
            {/* NOTE: This syncs across ALL charts on the page */}
            <TimeframeSelect
              value={timeframe}
              onChange={(tf) => setTimeframe(tf as Timeframe)}
            />
          </div>
        </div>

        {/* ── MARKET SUMMARY CARDS ────────────────────── */}
        {/* Nifty, Sensex, S&P, BTC, ETH, VIX */}
        {data && (
          <MarketCards
            bubbles={data.bubbles}
            className="mb-4"
          />
        )}

        {/* ── MAIN TWO-COLUMN LAYOUT ──────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4 mb-4">

          {/* ── BUBBLE HEATMAP ────────────────────────── */}
          {/* Main feature — Plotly Scattergl WebGL chart */}
          <div className="bg-card border rounded-xl p-4">
            <div className="text-xs font-medium text-muted-foreground mb-3">
              Bubble heatmap — market cap rank vs {timeframe} performance
            </div>
            {data && (
              <HeatmapChart
                bubbles={data.bubbles}
                timeframe={timeframe}
                height={320}
              />
            )}
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-green-100 border border-green-600 inline-block" />
                Positive
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-red-100 border border-red-600 inline-block" />
                Negative
              </span>
              <span className="ml-auto">
                Bubble size = market cap · X = cap rank · Y = % change
              </span>
            </div>
          </div>

          {/* ── TOP MOVERS SIDEBAR ────────────────────── */}
          {data && (
            <TopMovers
              gainers={data.top_movers?.gainers ?? []}
              losers={data.top_movers?.losers ?? []}
            />
          )}
        </div>

        {/* ── AI MARKET INSIGHT ───────────────────────── */}
        {data?.market_insight && (
          <div className="bg-card border rounded-xl p-4 mb-4">
            <div className="text-xs font-medium text-muted-foreground mb-2">
              AI market insight
            </div>
            <p className="text-sm font-medium">{data.market_insight.headline}</p>
            <p className="text-sm text-muted-foreground mt-1">{data.market_insight.summary}</p>
            <p className="text-xs text-muted-foreground mt-2">{data.market_insight.disclaimer}</p>
          </div>
        )}

        {/* ── SECTOR PERFORMANCE BARS ─────────────────── */}
        {data && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="bg-card border rounded-xl p-4">
              <div className="text-xs font-medium text-muted-foreground mb-3">
                India sectors — {timeframe} %
              </div>
              <SectorBars
                bubbles={data.bubbles.filter(b => b.market === "india")}
                height={200}
              />
            </div>
            <div className="bg-card border rounded-xl p-4">
              <div className="text-xs font-medium text-muted-foreground mb-3">
                US sectors — {timeframe} %
              </div>
              <SectorBars
                bubbles={data.bubbles.filter(b => b.market === "us")}
                height={200}
              />
            </div>
            <div className="bg-card border rounded-xl p-4">
              <div className="text-xs font-medium text-muted-foreground mb-3">
                Crypto — {timeframe} %
              </div>
              <SectorBars
                bubbles={data.bubbles.filter(b => b.market === "crypto")}
                height={200}
              />
            </div>
          </div>
        )}

        {/* ── DISCLAIMER ──────────────────────────────── */}
        {/* Always visible — legal requirement */}
        <Disclaimer />

      </main>
    </div>
  )
}
