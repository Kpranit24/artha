// =============================================================
// frontend/app/earnings/page.tsx
// PURPOSE:  Earnings calendar and results page
//
// WHAT IT SHOWS:
//   - Upcoming earnings calendar (next 14 days)
//   - Recent results with beat/miss summary
//   - Filter by India / US market
//
// DATA:
//   Currently static — earnings dates change frequently
//   TODO: Wire to earnings API (Alpha Vantage free tier has earnings)
//   Endpoint: https://www.alphavantage.co/query?function=EARNINGS_CALENDAR
//
// UPGRADE PATH:
//   Alpha Vantage free: 5 req/min earnings calendar
//   Finnhub free: basic earnings calendar
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Disclaimer } from "@/components/ui"
import { cn } from "@/lib/utils"


// Upcoming earnings — update weekly
// TODO: Replace with live API call
const UPCOMING = [
  { date: "Mar 20", symbol: "TCS",       name: "Tata Consultancy",   market: "India", eps_est: "₹28.4",    rev_est: "₹63,400Cr", beats: 4 },
  { date: "Mar 20", symbol: "HDFC Life", name: "HDFC Life Insurance",market: "India", eps_est: "₹1.82",    rev_est: "₹8,200Cr",  beats: 3 },
  { date: "Mar 21", symbol: "NVDA",      name: "NVIDIA",             market: "US",    eps_est: "$5.60",     rev_est: "$43.2B",    beats: 6 },
  { date: "Mar 21", symbol: "META",      name: "Meta Platforms",     market: "US",    eps_est: "$5.15",     rev_est: "$41.3B",    beats: 4 },
  { date: "Mar 22", symbol: "BAJFIN",    name: "Bajaj Finance",      market: "India", eps_est: "₹56.1",    rev_est: "₹14,800Cr", beats: 2 },
  { date: "Mar 24", symbol: "MSFT",      name: "Microsoft",          market: "US",    eps_est: "$2.84",     rev_est: "$68.4B",    beats: 5 },
  { date: "Mar 25", symbol: "RELIANCE",  name: "Reliance Industries",market: "India", eps_est: "₹38.2",    rev_est: "₹2,45,000Cr",beats: 3 },
  { date: "Apr 02", symbol: "INFY",      name: "Infosys",            market: "India", eps_est: "₹22.4",    rev_est: "₹42,000Cr", beats: 4 },
]

const RECENT = [
  {
    symbol: "INFY", name: "Infosys", market: "India",
    eps_actual: "₹22.1", eps_est: "₹21.4", beat: true,  move: "+3.2%",
    verdict: "Beat on margins. FY26 CC revenue guidance raised to 4.5–7%. BFSI recovery noted.",
    date: "Mar 13"
  },
  {
    symbol: "WIPRO", name: "Wipro", market: "India",
    eps_actual: "₹3.18", eps_est: "₹3.22", beat: false, move: "-1.8%",
    verdict: "Revenue missed estimates. Weak BFSI vertical dragged Q4 performance.",
    date: "Mar 12"
  },
  {
    symbol: "AAPL", name: "Apple", market: "US",
    eps_actual: "$2.40", eps_est: "$2.35", beat: true,  move: "+1.5%",
    verdict: "Services revenue hit all-time record at $26.3B. iPhone units slightly below expectations.",
    date: "Mar 10"
  },
  {
    symbol: "NVDA", name: "NVIDIA", market: "US",
    eps_actual: "$5.16", eps_est: "$4.82", beat: true,  move: "+6.8%",
    verdict: "Blackwell revenue exceeded expectations. Data centre at $30.8B. FY27 guidance strong.",
    date: "Mar 05"
  },
]


export default function EarningsPage() {
  const router  = useRouter()
  const [market, setMarket] = useState("all")
  const [tab,    setTab]    = useState<"upcoming" | "results">("upcoming")

  const filteredUpcoming = UPCOMING.filter(
    e => market === "all" || e.market.toLowerCase() === market
  )
  const filteredRecent = RECENT.filter(
    e => market === "all" || e.market.toLowerCase() === market
  )

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-4">

      {/* Controls */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
          <button
            onClick={() => setTab("upcoming")}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
              tab === "upcoming" ? "bg-background shadow-sm" : "text-muted-foreground"
            )}
          >
            Upcoming
          </button>
          <button
            onClick={() => setTab("results")}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
              tab === "results" ? "bg-background shadow-sm" : "text-muted-foreground"
            )}
          >
            Recent results
          </button>
        </div>

        <div className="flex gap-1">
          {["all", "india", "us"].map(m => (
            <button
              key={m}
              onClick={() => setMarket(m)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors capitalize",
                market === m
                  ? "bg-foreground text-background"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {m === "all" ? "All" : m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Upcoming earnings */}
      {tab === "upcoming" && (
        <div className="bg-card border rounded-xl overflow-hidden mb-4">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                {["Date", "Ticker", "Company", "Market", "Est. EPS", "Est. revenue", "Past beats"].map(h => (
                  <th key={h} className="text-left text-[11px] text-muted-foreground font-medium px-4 py-3 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredUpcoming.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-sm text-muted-foreground">
                    No upcoming earnings in this filter.
                  </td>
                </tr>
              )}
              {filteredUpcoming.map((e, i) => (
                <tr
                  key={i}
                  onClick={() => router.push(`/ticker/${e.market.toLowerCase()}/${e.symbol}`)}
                  className="border-b border-border/50 hover:bg-muted/40 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 text-muted-foreground tabular-nums whitespace-nowrap">{e.date}</td>
                  <td className="px-4 py-3 font-semibold">{e.symbol}</td>
                  <td className="px-4 py-3 text-muted-foreground">{e.name}</td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded font-medium",
                      e.market === "India"
                        ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400"
                        : "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
                    )}>
                      {e.market}
                    </span>
                  </td>
                  <td className="px-4 py-3 tabular-nums">{e.eps_est}</td>
                  <td className="px-4 py-3 tabular-nums text-muted-foreground">{e.rev_est}</td>
                  <td className="px-4 py-3">
                    <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                      +{e.beats} of last 4
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Recent results */}
      {tab === "results" && (
        <div className="flex flex-col gap-3 mb-4">
          {filteredRecent.length === 0 && (
            <div className="text-center py-8 text-sm text-muted-foreground bg-card border rounded-xl">
              No recent results in this filter.
            </div>
          )}
          {filteredRecent.map((r, i) => (
            <div
              key={i}
              onClick={() => router.push(`/ticker/${r.market.toLowerCase()}/${r.symbol}`)}
              className="bg-card border rounded-xl p-4 hover:bg-muted/30 cursor-pointer transition-colors"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{r.symbol}</span>
                  <span className="text-xs text-muted-foreground">{r.name}</span>
                  <span className={cn(
                    "text-[10px] px-1.5 py-0.5 rounded font-medium",
                    r.market === "India"
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400"
                      : "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
                  )}>
                    {r.market}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded font-medium",
                    r.beat
                      ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
                      : "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400"
                  )}>
                    {r.beat ? "Beat" : "Miss"} {r.move}
                  </span>
                  <span className="text-[10px] text-muted-foreground">{r.date}</span>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2">
                <span>EPS: <span className="font-medium text-foreground">{r.eps_actual}</span> vs est. {r.eps_est}</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{r.verdict}</p>
            </div>
          ))}
        </div>
      )}

      <Disclaimer />
    </div>
  )
}
