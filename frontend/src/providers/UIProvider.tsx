import React, { createContext, useContext, useState, useEffect } from "react"

interface UIContextType {
  isPrivacyMode: boolean
  togglePrivacyMode: () => void
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

  useEffect(() => {
    localStorage.setItem("privacy-mode", String(isPrivacyMode))
    if (isPrivacyMode) {
      document.body.classList.add("privacy-enabled")
    } else {
      document.body.classList.remove("privacy-enabled")
    }
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
