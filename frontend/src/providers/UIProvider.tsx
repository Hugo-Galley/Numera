import React, { createContext, useContext, useState, useEffect } from "react"
import { startPrivacyScanner } from "@/lib/privacyScanner"

interface UIContextType {
  isPrivacyMode: boolean
  togglePrivacyMode: () => void
  hideHoldingValues: boolean
  setHideHoldingValues: (hide: boolean) => void
  isSearchOpen: boolean
  setSearchOpen: (open: boolean) => void
}

const UIContext = createContext<UIContextType | undefined>(undefined)

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [isSearchOpen, setSearchOpen] = useState(false)
  const [isPrivacyMode, setIsPrivacyMode] = useState<boolean>(() => {
    const saved = localStorage.getItem("privacy-mode")
    return saved === "true"
  })

  // Comptes titres : n'afficher que le titre et le nombre de parts (pas de PRU, cours, valeurs)
  const [hideHoldingValues, setHideHoldingValues] = useState<boolean>(() => {
    return localStorage.getItem("hide-holding-values") === "true"
  })

  useEffect(() => {
    localStorage.setItem("hide-holding-values", String(hideHoldingValues))
  }, [hideHoldingValues])

  useEffect(() => {
    localStorage.setItem("privacy-mode", String(isPrivacyMode))
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
