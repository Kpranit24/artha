// =============================================================
// frontend/app/providers.tsx
// PURPOSE:  Wraps app with all React providers
//
// PROVIDERS:
//   QueryClientProvider → enables React Query (useQuery, useMutation)
//
// WHY SEPARATE FILE:
//   Next.js App Router needs "use client" for React Query provider
//   But layout.tsx is a server component
//   This pattern lets layout.tsx stay as a server component
//
// ADDING A NEW PROVIDER:
//   1. Import it here
//   2. Wrap children with it
//   3. Done — available everywhere in the app
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"

export function Providers({ children }: { children: React.ReactNode }) {
  // Create QueryClient once per app session
  // useState ensures it's not recreated on re-renders
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        // Don't refetch just because window regained focus
        // (would cause flash of loading on tab switch)
        refetchOnWindowFocus: false,
        // Keep data for 5 minutes before considering it stale
        staleTime: 5 * 60 * 1000,
        // Retry failed requests 3 times with exponential backoff
        retry: 3,
        retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
