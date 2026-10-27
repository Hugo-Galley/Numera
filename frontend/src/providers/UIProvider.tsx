import { safeStorage } from "@/lib/storage"
import React, { createContext, useContext, useState, useEffect } from "react"
import { startPrivacyScanner } from "@/lib/privacyScanner"

export type ThemePreference = "light" | "dark" | "system"

interface UIContextType {
  isPrivacyMode: boolean
  togglePrivacyMode: () => void
  setPrivacyMode: (enabled: boolean) => void
  theme: ThemePreference
  setTheme: (theme: ThemePreference) => void
  hideHoldingValues: boolean
  setHideHoldingValues: (hide: boolean) => void
  isSearchOpen: boolean
  setSearchOpen: (open: boolean) => void
}

const UIContext = createContext<UIContextType | undefined>(undefined)

// Même logique que le script en tête d'index.html (appliqué avant React, sans flash blanc)
function applyTheme(theme: ThemePreference) {
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches)
  document.documentElement.classList.toggle("dark", dark)
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#020617" : "#0f172a")
}

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [isSearchOpen, setSearchOpen] = useState(false)
  const [isPrivacyMode, setIsPrivacyMode] = useState<boolean>(() => {
    const saved = safeStorage.getItem("privacy-mode")
    return saved === "true"
  })

  // Thème propre à chaque appareil (clair, sombre ou celui du système)
  const [theme, setTheme] = useState<ThemePreference>(() => {
    const saved = safeStorage.getItem("theme")
    return saved === "light" || saved === "dark" ? saved : "system"
  })

  useEffect(() => {
    safeStorage.setItem("theme", theme)
    applyTheme(theme)
    if (theme !== "system") return
    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => applyTheme("system")
    media.addEventListener("change", onChange)
    return () => media.removeEventListener("change", onChange)
  }, [theme])

  // Comptes titres : n'afficher que le titre et le nombre de parts (pas de PRU, cours, valeurs)
  const [hideHoldingValues, setHideHoldingValues] = useState<boolean>(() => {
    return safeStorage.getItem("hide-holding-values") === "true"
  })

  useEffect(() => {
    safeStorage.setItem("hide-holding-values", String(hideHoldingValues))
  }, [hideHoldingValues])

  useEffect(() => {
    safeStorage.setItem("privacy-mode", String(isPrivacyMode))
    if (!isPrivacyMode) {
      document.body.classList.remove("privacy-enabled")
      return
    }
    document.body.classList.add("privacy-enabled")
    // Détection automatique de tous les montants (en plus de `amount-blur`)
    return startPrivacyScanner()
  }, [isPrivacyMode])

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setSearchOpen((open) => !open)
      }
    }

    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const togglePrivacyMode = () => setIsPrivacyMode((prev) => !prev)

  return (
    <UIContext.Provider value={{ 
      isPrivacyMode, 
      togglePrivacyMode, 
      setPrivacyMode: setIsPrivacyMode,
      theme,
      setTheme,
      hideHoldingValues,
      setHideHoldingValues,
      isSearchOpen, 
      setSearchOpen 
    }}>
      {children}
    </UIContext.Provider>
  )
}

export function useUI() {
  const context = useContext(UIContext)
  if (context === undefined) {
    throw new Error("useUI must be used within a UIProvider")
  }
  return context
}
