import React, { createContext, useContext, useState, useEffect } from "react"
import { isTokenExpired } from "@/lib/utils"

interface AuthContextType {
  token: string | null
  username: string | null
  login: (token: string) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function getUsernameFromToken(token: string | null): string | null {
  if (!token) return null
  try {
    const base64 = token.split(".")[1].replace(/-/g, '+').replace(/_/g, '/')
    const pad = base64.length % 4
    const payload = JSON.parse(atob(pad ? base64 + "=".repeat(4 - pad) : base64))
    return payload.sub || null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const savedToken = localStorage.getItem("token")
    if (savedToken && isTokenExpired(savedToken)) {
      localStorage.removeItem("token")
      return null
    }
    return savedToken
  })
  const username = getUsernameFromToken(token)

  useEffect(() => {
    // Vérifier l'expiration périodiquement (optionnel mais utile si l'onglet reste ouvert)
    const interval = setInterval(() => {
      if (token && isTokenExpired(token)) {
        logout()
      }
    }, 60000) // Toutes les minutes

    return () => clearInterval(interval)
  }, [token])

  const login = (newToken: string) => {
    localStorage.setItem("token", newToken)
    setToken(newToken)
  }

  const logout = () => {
    localStorage.removeItem("token")
    setToken(null)
  }

  const isAuthenticated = !!token

  return (
    <AuthContext.Provider value={{ token, username, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
