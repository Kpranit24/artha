// =============================================================
// frontend/next.config.ts
// PURPOSE:  Next.js configuration
// LAST UPDATED: March 2026
// =============================================================

import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Redirect root to dashboard
  async redirects() {
    return [
      {
        source:      "/",
        destination: "/dashboard",
        permanent:   false,
      },
    ]
  },

  // Allow images from these domains (for stock logos in future)
  images: {
    domains: ["assets.coingecko.com"],
  },

  // Bundle analyzer (uncomment to analyze bundle size)
  // Run: ANALYZE=true npm run build
  // ...(process.env.ANALYZE === "true" && {
  //   experimental: { bundleAnalyzer: { enabled: true } }
  // }),
}

export default nextConfig
