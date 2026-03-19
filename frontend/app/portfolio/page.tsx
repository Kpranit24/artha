// =============================================================
// frontend/app/portfolio/page.tsx
// PURPOSE:  Portfolio tracker page with live P&L
//
// WHAT IT SHOWS:
//   - Summary cards: total value, invested, P&L, P&L%
//   - Allocation donut chart (India / US / Crypto)
//   - Holdings table with live prices and individual P&L
//   - Add holding form
//
// DATA:
//   GET /api/portfolio — requires auth
//   Crypto prices: live (CoinGecko)
//   US stocks: live (Yahoo)
//   India stocks: ~1min delayed (yfinance)
//
// AUTH:
//   For now: works with demo data if not logged in
//   In production: requires Supabase auth
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, REFETCH_INTERVAL_MS } from "@/lib/api"
import { Disclaimer, LoadingState, ErrorState } from "@/components/ui"
import { cn, formatPrice, formatChange, formatLargeNumber } from "@/lib/utils"


export default function PortfolioPage() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newHolding, setNewHolding] = useState({
    symbol: "", market: "crypto", quantity: "", avg_cost: "", currency: "USD"
  })

  // Fetch portfolio data — refreshes every 30s (slower than heatmap, saves API calls)
  const { data, isLoading, isError, error } = useQuery({
    queryKey:        ["portfolio"],
    queryFn:         () => api.portfolio.get(),
    refetchInterval: REFETCH_INTERVAL_MS * 2,  // 30s
  })

  // Add holding mutation
  const addMutation = useMutation({
    mutationFn: api.portfolio.updateHolding,
    onSuccess:  () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio"] })
      setShowAddForm(false)
      setNewHolding({ symbol: "", market: "crypto", quantity: "", avg_cost: "", currency: "USD" })
    },
  })

  if (isLoading) return <LoadingState message="Loading portfolio..." />
  if (isError)   return <ErrorState message={error instanceof Error ? error.message : "Failed to load portfolio"} />
  if (!data)     return null

  const pnlPositive = data.unrealized_pnl >= 0

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-4">

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        {[
          { label: "Total value",    value: formatLargeNumber(data.total_value),    sub: "Live + reference" },
          { label: "Invested",       value: formatLargeNumber(data.total_invested), sub: "Cost basis"       },
          {
            label: "Unrealised P&L",
            value: (pnlPositive ? "+" : "") + formatLargeNumber(Math.abs(data.unrealized_pnl)),
            sub:   formatChange(data.unrealized_pnl_pct),
            color: pnlPositive ? "text-green-600" : "text-red-600"
          },
          {
            label: "Return",
            value: (pnlPositive ? "+" : "") + data.unrealized_pnl_pct.toFixed(2) + "%",
            sub:   "All time",
            color: pnlPositive ? "text-green-600" : "text-red-600"
          },
        ].map(card => (
          <div key={card.label} className="bg-muted/50 rounded-lg p-3">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{card.label}</div>
            <div className={cn("text-xl font-semibold", card.color)}>{card.value}</div>
            <div className="text-xs text-muted-foreground mt-0.5">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Allocation + Holdings */}
      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-4">

        {/* Allocation sidebar */}
        <div className="bg-card border rounded-xl p-4">
          <div className="text-xs font-medium text-muted-foreground mb-3">Allocation</div>
          {data.allocation?.map((alloc: any) => (
            <div key={alloc.market} className="mb-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium capitalize">{alloc.market}</span>
                <span className="text-muted-foreground">{alloc.pct}%</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${alloc.pct}%`,
                    background: { india: "#185FA5", us: "#1D9E75", crypto: "#D85A30" }[alloc.market as string] ?? "#888"
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Holdings table */}
        <div className="bg-card border rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-medium text-muted-foreground">Holdings</div>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="text-xs px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-lg transition-colors"
            >
              + Add holding
            </button>
          </div>

          {/* Add holding form */}
          {showAddForm && (
            <div className="bg-muted/50 rounded-lg p-3 mb-3 grid grid-cols-2 gap-2">
              {[
                { key: "symbol",   label: "Symbol",     placeholder: "BTC, INFY, AAPL" },
                { key: "avg_cost", label: "Avg cost",   placeholder: "62000"            },
                { key: "quantity", label: "Quantity",   placeholder: "0.5"              },
              ].map(field => (
                <div key={field.key}>
                  <label className="text-[10px] text-muted-foreground block mb-0.5">{field.label}</label>
                  <input
                    type={field.key === "symbol" ? "text" : "number"}
                    placeholder={field.placeholder}
                    value={(newHolding as any)[field.key]}
                    onChange={e => setNewHolding(prev => ({ ...prev, [field.key]: e.target.value }))}
                    className="w-full text-xs bg-background border border-border rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
              ))}
              <div>
                <label className="text-[10px] text-muted-foreground block mb-0.5">Market</label>
                <select
                  value={newHolding.market}
                  onChange={e => setNewHolding(prev => ({ ...prev, market: e.target.value, currency: e.target.value === "india" ? "INR" : "USD" }))}
                  className="w-full text-xs bg-background border border-border rounded px-2 py-1.5 focus:outline-none"
                >
                  <option value="crypto">Crypto</option>
                  <option value="india">India</option>
                  <option value="us">US</option>
                </select>
              </div>
              <div className="col-span-2 flex gap-2">
                <button
                  onClick={() => addMutation.mutate({
                    symbol:   newHolding.symbol.toUpperCase(),
                    market:   newHolding.market,
                    quantity: parseFloat(newHolding.quantity),
                    avg_cost: parseFloat(newHolding.avg_cost),
                    currency: newHolding.currency,
                  })}
                  disabled={!newHolding.symbol || !newHolding.quantity || !newHolding.avg_cost}
                  className="flex-1 text-xs py-1.5 bg-foreground text-background rounded-lg disabled:opacity-40"
                >
                  {addMutation.isPending ? "Saving..." : "Save holding"}
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="text-xs px-3 py-1.5 bg-muted rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Holdings table */}
          {data.holdings.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              No holdings yet. Click "+ Add holding" to start tracking.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    {["Ticker", "Market", "Qty", "Avg cost", "Live price", "P&L", "P&L %", "Weight"].map(h => (
                      <th key={h} className="text-left text-[11px] text-muted-foreground font-medium pb-2 pr-3 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.holdings.map((h: any) => {
                    const up = (h.unrealized_pnl ?? 0) >= 0
                    return (
                      <tr key={h.symbol} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                        <td className="py-2.5 pr-3 font-semibold">{h.symbol}</td>
                        <td className="py-2.5 pr-3">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400">
                            {h.market}
                          </span>
                        </td>
                        <td className="py-2.5 pr-3 tabular-nums">{h.quantity}</td>
                        <td className="py-2.5 pr-3 tabular-nums text-muted-foreground">
                          {h.currency === "INR" ? "₹" : "$"}{h.avg_cost.toLocaleString()}
                        </td>
                        <td className="py-2.5 pr-3 tabular-nums">
                          {h.live_price
                            ? (h.currency === "INR" ? "₹" : "$") + h.live_price.toLocaleString()
                            : <span className="text-muted-foreground">—</span>
                          }
                          {h.is_live && <span className="ml-1 w-1 h-1 rounded-full bg-green-500 inline-block" />}
                        </td>
                        <td className={cn("py-2.5 pr-3 tabular-nums font-medium", up ? "text-green-600" : "text-red-600")}>
                          {h.unrealized_pnl != null
                            ? (up ? "+" : "") + (h.currency === "INR" ? "₹" : "$") + Math.abs(h.unrealized_pnl).toLocaleString()
                            : "—"
                          }
                        </td>
                        <td className={cn("py-2.5 pr-3", up ? "text-green-600" : "text-red-600")}>
                          {h.unrealized_pnl_pct != null
                            ? (up ? "+" : "") + h.unrealized_pnl_pct.toFixed(2) + "%"
                            : "—"
                          }
                        </td>
                        <td className="py-2.5 text-muted-foreground">
                          {h.current_value && data.total_value
                            ? (h.current_value / data.total_value * 100).toFixed(1) + "%"
                            : "—"
                          }
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <Disclaimer />
    </div>
  )
}
