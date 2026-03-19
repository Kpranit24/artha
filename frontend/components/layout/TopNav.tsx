// =============================================================
// frontend/components/layout/TopNav.tsx
// PURPOSE:  Main navigation bar across top of every page
//
// TABS:
//   Markets | Portfolio | Screener | Earnings | Macro
//
// FEATURES:
//   - Active tab highlighted
//   - App name/logo on left
//   - "Not financial advice" disclaimer on right (small)
//   - Responsive: collapses on mobile
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { href: "/dashboard",  label: "Markets"   },
  { href: "/portfolio",  label: "Portfolio" },
  { href: "/screener",   label: "Screener"  },
  { href: "/earnings",   label: "Earnings"  },
  { href: "/macro",      label: "Macro"     },
]

export function TopNav() {
  const pathname = usePathname()

  return (
    <header className="border-b border-border bg-background/95 backdrop-blur sticky top-0 z-50">
      <div className="max-w-[1400px] mx-auto px-4 h-12 flex items-center justify-between gap-4">

        {/* Logo + name */}
        <Link href="/dashboard" className="flex items-center gap-2 flex-shrink-0">
          <div className="w-6 h-6 bg-blue-600 rounded flex items-center justify-center">
            <svg width="12" height="12" viewBox="0 0 18 18" fill="none">
              <path d="M4 13L9 5L14 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M6.5 10H11.5" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="font-semibold text-sm text-foreground">
            Artha
          </span>
          <span className="text-[10px] bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 px-1.5 py-0.5 rounded font-medium">
            FREE
          </span>
        </Link>

        {/* Navigation tabs */}
        <nav className="flex items-center gap-0.5">
          {NAV_ITEMS.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "px-3 py-1.5 text-sm rounded-md transition-colors",
                pathname === item.href || pathname.startsWith(item.href + "/")
                  ? "bg-muted text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Disclaimer — right side */}
        <span className="text-[10px] text-muted-foreground/60 hidden lg:block flex-shrink-0">
          Not financial advice
        </span>

      </div>
    </header>
  )
}
