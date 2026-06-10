import React, { createContext, useContext, useState, useEffect } from "react"
import { isTokenExpired } from "@/lib/utils"

interface AuthContextType {
  token: string | null
  login: (token: string) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const savedToken = localStorage.getItem("token")
    if (savedToken && isTokenExpired(savedToken)) {
      localStorage.removeItem("token")
      return null
    }
    return savedToken
  })

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
    <AuthContext.Provider value={{ token, login, logout, isAuthenticated }}>
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
