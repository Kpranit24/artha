// =============================================================
// frontend/app/layout.tsx
// PURPOSE:  Root layout — wraps all pages
//           Sets up React Query, fonts, metadata
//
// WHAT IT DOES:
//   1. Wraps app in React Query provider (enables useQuery everywhere)
//   2. Sets page metadata (title, description for SEO)
//   3. Applies Tailwind base styles
//   4. Adds top navigation bar
//
// LAST UPDATED: March 2026
// =============================================================

import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Providers } from "./providers"
import { TopNav } from "@/components/layout/TopNav"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title:       "Artha — Free Market Intelligence",
  description: "Free Perplexity Finance alternative. India stocks, US equities, crypto — all in one dashboard with AI insights. Built for everyone.",
  keywords:    ["stock market", "nifty", "crypto", "portfolio tracker", "india stocks", "free finance dashboard"],
  openGraph: {
    title:       "Artha",
    description: "Free AI-powered market dashboard — India, US, Crypto",
    type:        "website",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <TopNav />
          {children}
        </Providers>
      </body>
    </html>
  )
}
