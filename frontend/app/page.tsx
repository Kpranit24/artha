// =============================================================
// frontend/app/page.tsx
// PURPOSE:  Public landing page — shown before login
//           Explains what the app is and why it's free
//
// LAST UPDATED: March 2026
// =============================================================

import Link from "next/link"


export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">

      {/* Nav */}
      <nav className="border-b border-border px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 18 18" fill="none">
              <path d="M4 13L9 5L14 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M6.5 10H11.5" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="font-bold text-lg">Artha</span>
          <span className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 px-2 py-0.5 rounded font-medium">
            FREE
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/auth" className="text-sm text-muted-foreground hover:text-foreground">
            Sign in
          </Link>
          <Link
            href="/auth"
            className="text-sm bg-foreground text-background px-4 py-2 rounded-lg font-medium hover:opacity-90"
          >
            Get started free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-400 text-xs font-medium px-3 py-1.5 rounded-full mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          Live data · India + US + Crypto
        </div>

        <h1 className="text-5xl font-bold tracking-tight mb-4 leading-tight">
          Artha.<br />
          <span className="text-muted-foreground">Markets made free.</span>
        </h1>

        <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
          AI-powered market dashboard covering Nifty, S&amp;P 500, and crypto.
          Live prices, portfolio tracker, bubble heatmap, and Claude AI insights —
          everything Perplexity Finance charges $20/month for. Free, forever.
        </p>

        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link
            href="/auth"
            className="px-6 py-3 bg-foreground text-background rounded-xl font-semibold hover:opacity-90 transition-opacity"
          >
            Start for free — no credit card
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 bg-muted text-foreground rounded-xl font-semibold hover:bg-muted/80 transition-colors"
          >
            View demo
          </Link>
        </div>

        <p className="text-xs text-muted-foreground mt-4">
          Not financial advice. All data for informational purposes only.
        </p>
      </section>

      {/* Features grid */}
      <section className="max-w-5xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              icon: "📊",
              title: "Live bubble heatmap",
              desc: "Market cap vs performance — see which sectors and stocks are moving at a glance. India + US + Crypto in one view."
            },
            {
              icon: "🤖",
              title: "AI insights (Claude)",
              desc: "Click any ticker for an instant AI analysis — what's driving the move, bull case, bear case, key factors."
            },
            {
              icon: "💼",
              title: "Portfolio tracker",
              desc: "Track your NSE, NYSE, and crypto holdings together. Live P&L calculated in real time."
            },
            {
              icon: "🔔",
              title: "Price alerts",
              desc: "Set price thresholds. Get Telegram notifications the moment BTC drops below $80K or TCS breaks ₹4000."
            },
            {
              icon: "🔍",
              title: "Stock screener",
              desc: "Filter by top gainers, losers, volume, near ATH, or best 7-day. India, US, and crypto in one screener."
            },
            {
              icon: "📈",
              title: "Macro dashboard",
              desc: "RBI rate, Fed rate, India VIX, fear & greed index, upcoming earnings — all in one macro overview."
            },
          ].map(f => (
            <div key={f.title} className="bg-card border border-border rounded-xl p-5">
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-semibold mb-1.5">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing comparison */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <h2 className="text-2xl font-bold text-center mb-8">
          Same features. 0% of the cost.
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-card border border-border rounded-xl p-5">
            <div className="text-sm font-medium text-muted-foreground mb-1">Perplexity Artha</div>
            <div className="text-3xl font-bold mb-4">$20<span className="text-base font-normal text-muted-foreground">/mo</span></div>
            {["AI insights", "Live heatmap", "Stock screener", "Portfolio tracker", "Price alerts", "India stocks"].map(f => (
              <div key={f} className="flex items-center gap-2 text-sm py-1">
                <span className="text-green-600">✓</span> {f}
              </div>
            ))}
          </div>
          <div className="bg-card border-2 border-blue-500 rounded-xl p-5 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs px-3 py-1 rounded-full font-medium">
              This app
            </div>
            <div className="text-sm font-medium text-muted-foreground mb-1">Artha</div>
            <div className="text-3xl font-bold mb-4 text-blue-600">Free<span className="text-base font-normal text-muted-foreground"> forever</span></div>
            {["AI insights (Claude)", "Live heatmap (WebGL)", "Stock screener", "Portfolio tracker", "Price alerts (Telegram)", "India stocks (NSE/BSE)"].map(f => (
              <div key={f} className="flex items-center gap-2 text-sm py-1">
                <span className="text-green-600">✓</span> {f}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-2xl mx-auto px-6 py-16 text-center">
        <h2 className="text-3xl font-bold mb-3">Ready to start?</h2>
        <p className="text-muted-foreground mb-6">
          Free account. No credit card. Takes 30 seconds.
        </p>
        <Link
          href="/auth"
          className="inline-block px-8 py-3 bg-foreground text-background rounded-xl font-semibold hover:opacity-90"
        >
          Create free account
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        <p className="mb-1">Built with ❤️ as a free alternative to paid finance dashboards.</p>
        <p>Not financial advice. All market data for informational purposes only. Past performance does not guarantee future results.</p>
      </footer>

    </div>
  )
}
