// =============================================================
// frontend/components/charts/HeatmapChart.tsx
// PURPOSE:  Bubble heatmap chart using Plotly.js Scattergl
//           The main visual feature of the dashboard
//
// WHY PLOTLY SCATTERGL:
//   Uses WebGL rendering — handles 1000+ bubbles at 60fps
//   Regular Plotly Scatter maxes out at ~200 bubbles
//   This matches Perplexity Finance's performance secret
//
// AXES:
//   X = market cap rank (1 = largest cap)
//   Y = % change for selected timeframe
//   Bubble size = relative market cap
//   Color = green (up) / red (down)
//
// INTERACTIONS:
//   Hover = tooltip with price, % change, market cap
//   Click = navigate to full ticker page
//
// SYNCHRONIZED TIMEFRAME:
//   This chart does NOT own the timeframe state
//   Parent (dashboard/page.tsx) owns it
//   All charts on the page update when timeframe changes
//   This is the "synchronized timeframe" feature from architecture
//
// UPGRADE PATH:
//   Currently using dynamic import to avoid SSR issues
//   At very high scale: pre-render static PNG on server,
//   replace with WebGL version once hydrated
//
// AI AGENT MONITORS:
//   frontend_agent → alerts if chart throws render errors
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import type { HeatmapBubble, Timeframe } from "@/types/market"


interface HeatmapChartProps {
  bubbles:   HeatmapBubble[]
  timeframe: Timeframe
  height?:   number
  onBubbleClick?: (symbol: string, market: string) => void
}


export function HeatmapChart({
  bubbles,
  timeframe,
  height = 320,
  onBubbleClick,
}: HeatmapChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const plotRef      = useRef<any>(null)
  const router       = useRouter()
  const [isLoaded,   setIsLoaded]   = useState(false)
  const [PlotlyLib,  setPlotlyLib]  = useState<any>(null)


  // ── LOAD PLOTLY ─────────────────────────────────────────
  // Dynamic import — Plotly is large (~3MB), load lazily
  // This keeps the initial page load fast
  useEffect(() => {
    import("plotly.js-dist-min").then((Plotly) => {
      setPlotlyLib(Plotly)
      setIsLoaded(true)
    })
  }, [])


  // ── RENDER / UPDATE CHART ───────────────────────────────
  // Re-renders when bubbles or timeframe changes
  useEffect(() => {
    if (!isLoaded || !PlotlyLib || !containerRef.current || !bubbles.length) {
      return
    }

    renderChart(PlotlyLib, containerRef.current, bubbles, timeframe, height)

    // Click handler — navigate to ticker page
    containerRef.current.on("plotly_click", (event: any) => {
      const point = event.points?.[0]
      if (!point) return

      const bubble = bubbles[point.pointIndex] || bubbles.find(
        b => b.symbol === point.text
      )

      if (!bubble) return

      if (onBubbleClick) {
        onBubbleClick(bubble.symbol, bubble.market)
      } else {
        // Default: navigate to ticker page
        router.push(`/ticker/${bubble.market}/${bubble.symbol}`)
      }
    })

  }, [isLoaded, PlotlyLib, bubbles, timeframe, height])


  // ── LOADING STATE ───────────────────────────────────────
  if (!isLoaded) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-muted-foreground text-sm"
      >
        Loading chart...
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      style={{ height, width: "100%" }}
      // Prevent tooltip collision with parent tooltips
      className="relative"
    />
  )
}


// ── CHART RENDERER ─────────────────────────────────────────
// Separated from component for clarity and testability

function renderChart(
  Plotly: any,
  container: HTMLElement,
  bubbles: HeatmapBubble[],
  timeframe: string,
  height: number
) {
  // Build Plotly dataset
  // One dataset per bubble = individual hover tooltips
  // This is more verbose but gives us full control over styling
  const datasets = bubbles.map(bubble => ({
    type:     "scattergl",  // WebGL = handles 1000+ bubbles at 60fps
    mode:     "markers+text",
    x:        [bubble.x],
    y:        [bubble.y],
    text:     [bubble.symbol],
    textposition: "middle center",
    textfont: {
      size:   bubble.size > 16 ? 11 : 9,
      color:  bubble.y >= 0 ? "#3B6D11" : "#A32D2D",
      family: "system-ui, sans-serif",
    },
    marker: {
      size:   bubble.size,
      color:  bubble.color,
      line: {
        color: bubble.border_color || (bubble.y >= 0 ? "#3B6D11" : "#A32D2D"),
        width: 1.5,
      },
    },
    hovertemplate:
      `<b>${bubble.name}</b><br>` +
      `${bubble.symbol} · ${bubble.market.toUpperCase()}<br>` +
      `${bubble.y >= 0 ? "+" : ""}${bubble.y.toFixed(2)}% (${timeframe})<br>` +
      `Price: ${bubble.currency === "INR" ? "₹" : "$"}${bubble.price.toLocaleString()}<br>` +
      (bubble.market_cap ? `Mkt cap: $${formatLargeNumber(bubble.market_cap)}<br>` : "") +
      (bubble.is_live ? "" : "<i>Delayed data</i><br>") +
      `<extra></extra>`,
    name:       bubble.symbol,
    showlegend: false,
  }))

  const layout = {
    height,
    paper_bgcolor: "rgba(0,0,0,0)",  // Transparent — inherits theme
    plot_bgcolor:  "rgba(0,0,0,0)",
    margin:        { t: 10, r: 10, b: 40, l: 50 },
    xaxis: {
      title:     { text: "Market cap rank (1 = largest)", font: { size: 11 } },
      showgrid:  true,
      gridcolor: "rgba(128,128,128,0.1)",
      zeroline:  false,
    },
    yaxis: {
      title:     { text: `${timeframe} change %`, font: { size: 11 } },
      showgrid:  true,
      gridcolor: "rgba(128,128,128,0.1)",
      zeroline:  true,
      zerolinecolor: "rgba(128,128,128,0.3)",
      tickformat: ".1f",
      ticksuffix: "%",
    },
    hoverlabel: {
      bgcolor:   "white",
      bordercolor: "rgba(0,0,0,0.1)",
      font:      { size: 12, family: "system-ui, sans-serif" },
    },
    // No legend — labels are on the bubbles themselves
    showlegend: false,
  }

  const config = {
    responsive:    true,
    displayModeBar: false,  // Hide Plotly toolbar (we have our own controls)
    doubleClick:   "reset",
  }

  // Use react() to create or update in place
  // This avoids full chart remount on data refresh
  if ((container as any)._fullLayout) {
    // Chart already exists — just update the data
    Plotly.react(container, datasets, layout, config)
  } else {
    // First render
    Plotly.newPlot(container, datasets, layout, config)
  }
}


// ── HELPERS ────────────────────────────────────────────────

function formatLargeNumber(n: number): string {
  if (n >= 1e12) return `${(n / 1e12).toFixed(1)}T`
  if (n >= 1e9)  return `${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6)  return `${(n / 1e6).toFixed(1)}M`
  return n.toLocaleString()
}
