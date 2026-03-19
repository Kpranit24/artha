// =============================================================
// frontend/components/charts/CandlestickChart.tsx
// PURPOSE:  OHLCV candlestick chart using Plotly.js
//
// WHAT IT SHOWS:
//   - Candlestick chart (open/high/low/close)
//   - Volume bars below
//   - Green candle = price closed higher than open
//   - Red candle   = price closed lower than open
//
// UPGRADE PATH:
//   Currently using Plotly candlestick (good performance)
//   For WebGL at 10K+ candles: use Plotly Scattergl instead
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useEffect, useRef, useState } from "react"

interface CandlePoint {
  timestamp: string
  open:      number
  high:      number
  low:       number
  close:     number
  volume:    number
}

interface CandlestickChartProps {
  data:     CandlePoint[]
  symbol:   string
  currency: "USD" | "INR"
  height?:  number
}

export function CandlestickChart({
  data,
  symbol,
  currency,
  height = 300,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    import("plotly.js-dist-min").then(Plotly => {
      setLoaded(true)
      if (!containerRef.current || !data.length) return

      const times  = data.map(d => d.timestamp)
      const open   = data.map(d => d.open)
      const high   = data.map(d => d.high)
      const low    = data.map(d => d.low)
      const close  = data.map(d => d.close)
      const volume = data.map(d => d.volume)

      const currencySymbol = currency === "INR" ? "₹" : "$"

      const candleTrace = {
        type: "candlestick",
        x:    times,
        open, high, low, close,
        name: symbol,
        increasing: { line: { color: "#3B6D11" }, fillcolor: "#EAF3DE" },
        decreasing: { line: { color: "#A32D2D" }, fillcolor: "#FCEBEB" },
        hovertemplate:
          `O: ${currencySymbol}%{open:,.2f}<br>` +
          `H: ${currencySymbol}%{high:,.2f}<br>` +
          `L: ${currencySymbol}%{low:,.2f}<br>` +
          `C: ${currencySymbol}%{close:,.2f}<extra></extra>`,
        xaxis: "x",
        yaxis: "y",
      }

      const volumeTrace = {
        type:   "bar",
        x:      times,
        y:      volume,
        name:   "Volume",
        marker: {
          color: close.map((c, i) =>
            c >= open[i] ? "rgba(59,109,17,0.4)" : "rgba(162,45,45,0.4)"
          )
        },
        hovertemplate: "Vol: %{y:,.0f}<extra></extra>",
        xaxis: "x",
        yaxis: "y2",
      }

      const layout = {
        height,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor:  "rgba(0,0,0,0)",
        margin:        { t: 8, r: 8, b: 30, l: 60 },
        xaxis: {
          type:       "date",
          showgrid:   false,
          rangeslider: { visible: false },
          tickfont:   { size: 10, color: "#888" },
        },
        yaxis: {
          showgrid:   true,
          gridcolor:  "rgba(128,128,128,0.08)",
          tickfont:   { size: 10, color: "#888" },
          tickprefix: currencySymbol,
          domain:     [0.2, 1],
        },
        yaxis2: {
          showgrid: false,
          tickfont: { size: 9, color: "#888" },
          domain:   [0, 0.15],
        },
        showlegend: false,
      }

      Plotly.react(containerRef.current, [candleTrace, volumeTrace], layout, {
        responsive:     true,
        displayModeBar: false,
      })
    })
  }, [data, symbol, currency, height])

  if (!loaded || !data.length) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-sm text-muted-foreground"
      >
        {!data.length ? "No chart data" : "Loading chart..."}
      </div>
    )
  }

  return <div ref={containerRef} style={{ height, width: "100%" }} />
}
