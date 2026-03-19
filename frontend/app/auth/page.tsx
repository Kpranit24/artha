// =============================================================
// frontend/app/auth/page.tsx
// PURPOSE:  Login / signup page
//
// FLOW:
//   1. User enters email + password
//   2. POST /auth/login → gets access_token
//   3. Token stored in sessionStorage
//   4. Redirected to /dashboard
//
// SUPABASE AUTH:
//   When SUPABASE_URL is set, uses Supabase Auth
//   Otherwise uses local JWT (dev mode)
//
// LAST UPDATED: March 2026
// =============================================================

"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { setAuthToken } from "@/lib/api"
import { cn } from "@/lib/utils"


const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"


export default function AuthPage() {
  const router  = useRouter()
  const [mode,     setMode]     = useState<"login" | "signup">("login")
  const [email,    setEmail]    = useState("")
  const [password, setPassword] = useState("")
  const [name,     setName]     = useState("")
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState("")
  const [success,  setSuccess]  = useState("")


  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError("")
    setSuccess("")

    const endpoint = mode === "login" ? "/auth/login" : "/auth/signup"
    const body     = mode === "login"
      ? { email, password }
      : { email, password, name }

    try {
      const resp = await fetch(`${API_URL}${endpoint}`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      })

      const data = await resp.json()

      if (!resp.ok) {
        setError(data.detail || "Something went wrong")
        return
      }

      if (mode === "signup") {
        setSuccess("Account created! Check your email to confirm, then log in.")
        setMode("login")
        return
      }

      // Login success — store token and redirect
      if (data.access_token) {
        setAuthToken(data.access_token)
        // Also store refresh token
        if (data.refresh_token) {
          sessionStorage.setItem("refresh_token", data.refresh_token)
        }
        router.push("/dashboard")
      }

    } catch (err) {
      setError("Cannot reach server. Check your connection.")
    } finally {
      setLoading(false)
    }
  }


  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
              <path d="M4 13L9 5L14 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M6.5 10H11.5" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="text-xl font-bold">Artha</span>
          <span className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 px-2 py-0.5 rounded font-medium">
            FREE
          </span>
        </div>

        {/* Card */}
        <div className="bg-card border border-border rounded-2xl p-8">

          {/* Tab switcher */}
          <div className="flex gap-1 bg-muted rounded-xl p-1 mb-6">
            <button
              onClick={() => { setMode("login"); setError(""); setSuccess(""); }}
              className={cn(
                "flex-1 py-2 text-sm font-medium rounded-lg transition-all",
                mode === "login"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              Sign in
            </button>
            <button
              onClick={() => { setMode("signup"); setError(""); setSuccess(""); }}
              className={cn(
                "flex-1 py-2 text-sm font-medium rounded-lg transition-all",
                mode === "signup"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              Create account
            </button>
          </div>

          {/* Success message */}
          {success && (
            <div className="mb-4 p-3 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-400 text-sm rounded-lg">
              {success}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-400 text-sm rounded-lg">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">

            {mode === "signup" && (
              <div>
                <label className="block text-xs text-muted-foreground mb-1.5">
                  Your name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Rahul Sharma"
                  className="w-full px-3 py-2.5 text-sm bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            )}

            <div>
              <label className="block text-xs text-muted-foreground mb-1.5">
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-3 py-2.5 text-sm bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div>
              <label className="block text-xs text-muted-foreground mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder={mode === "signup" ? "At least 8 characters" : "Your password"}
                required
                minLength={mode === "signup" ? 8 : 1}
                className="w-full px-3 py-2.5 text-sm bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !email || !password}
              className={cn(
                "w-full py-2.5 text-sm font-semibold rounded-lg transition-all",
                "bg-foreground text-background",
                "hover:opacity-90 active:scale-[0.98]",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
            >
              {loading
                ? "Please wait..."
                : mode === "login" ? "Sign in" : "Create free account"
              }
            </button>

          </form>

          {/* Footer */}
          <p className="text-center text-xs text-muted-foreground mt-6">
            {mode === "login" ? (
              <>No account? <button onClick={() => setMode("signup")} className="underline">Create one free</button></>
            ) : (
              <>Already have an account? <button onClick={() => setMode("login")} className="underline">Sign in</button></>
            )}
          </p>

        </div>

        {/* Disclaimer */}
        <p className="text-center text-[10px] text-muted-foreground mt-4">
          Not financial advice. All data for informational purposes only.
        </p>

      </div>
    </div>
  )
}
