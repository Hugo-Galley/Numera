import React, { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { 
  HandCoins,
  Search, 
  Wallet, 
  LayoutDashboard, 
  TrendingUp, 
  PiggyBank, 
  ArrowLeftRight, 
  Upload, 
  Settings,
  Receipt,
  ArrowRight,
  ShieldCheck,
  Landmark,
  ClipboardCheck,
  Gift,
  Sparkles,
  Repeat,
  CalendarDays,
  Calculator,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useUI } from "@/providers/UIProvider"
import { api } from "@/lib/api"
import { ScrollArea } from "@/components/ui/scroll-area"
import { formatCurrency, cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"

// Mêmes destinations que la barre latérale, plus des raccourcis vers les onglets (⌘K « calendrier »…)
const NAVIGATION = [
  { name: "Tableau de bord", href: "/", icon: LayoutDashboard },
  { name: "Bilan du mois", href: "/month/bilan", icon: Sparkles },
  { name: "Revue de mois", href: "/month/revue", icon: ClipboardCheck },
  { name: "Comparaison mensuelle", href: "/month/comparaison", icon: ArrowLeftRight },
  { name: "Bilan annuel", href: "/wrapped", icon: Gift },
  { name: "Centre d'actions", href: "/audit", icon: ShieldCheck },
  { name: "Comptes", href: "/accounts", icon: Wallet },
  { name: "Épargne", href: "/savings", icon: PiggyBank },
  { name: "Investissements", href: "/investments", icon: TrendingUp },
  { name: "Fiscalité", href: "/tax", icon: Landmark },
  { name: "Échéances (récurrences)", href: "/recurring", icon: Repeat },
  { name: "Calendrier", href: "/recurring?tab=calendar", icon: CalendarDays },
  { name: "Salaire", href: "/recurring?tab=salary", icon: Wallet },
  { name: "Remboursements", href: "/reimbursements", icon: HandCoins },
  { name: "Simulateur", href: "/tools", icon: Calculator },
  { name: "Importation", href: "/settings?tab=import", icon: Upload },
  { name: "Paramètres", href: "/settings", icon: Settings },
]

export function Omnibox() {
  const navigate = useNavigate()
  const { isSearchOpen, setSearchOpen, isPrivacyMode } = useUI()
  const [query, setQuery] = useState("")
  const [accounts, setAccounts] = useState<any[]>([])
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  // Mobile : plein écran, calé sur la zone réellement visible (clavier virtuel ouvert)
  const [viewport, setViewport] = useState<{ height: number; top: number } | null>(null)

  useEffect(() => {
    if (!isSearchOpen) return
    const vv = window.visualViewport
    if (!vv) return
    const update = () => setViewport({ height: vv.height, top: vv.offsetTop })
    update()
    vv.addEventListener("resize", update)
    vv.addEventListener("scroll", update)
    return () => {
      vv.removeEventListener("resize", update)
      vv.removeEventListener("scroll", update)
    }
  }, [isSearchOpen])

  useEffect(() => {
    if (isSearchOpen) {
      setQuery("")
      loadAccounts()
      setTransactions([])
      setActiveIndex(0)
    }
  }, [isSearchOpen])

  useEffect(() => {
    if (!query || query.length < 2) {
      setTransactions([])
      setActiveIndex(0)
      return
    }

    let isCurrent = true
    const timer = setTimeout(async () => {
      try {
        setLoading(true)
        const data = await api.get<any[]>(`/transactions?search=${encodeURIComponent(query)}&limit=10`)
        if (isCurrent) {
          setTransactions(data || [])
          setActiveIndex(0)
        }
      } catch (error) {
        if (isCurrent) {
          console.error("Failed to search transactions", error)
        }
      } finally {
        if (isCurrent) {
          setLoading(false)
        }
      }
    }, 300)

    return () => {
      isCurrent = false
      clearTimeout(timer)
    }
  }, [query])

  async function loadAccounts() {
    try {
      const data = await api.get<any[]>("/accounts")
      setAccounts(data || [])
    } catch (error) {
      console.error("Failed to load accounts for search", error)
    }
  }

  const filteredNavigation = NAVIGATION.filter((item) =>
    item.name.toLowerCase().includes(query.toLowerCase())
  ).map(item => ({ ...item, type: 'nav' }))

  const filteredAccounts = accounts.filter((acc) =>
    acc.name.toLowerCase().includes(query.toLowerCase())
  ).map(acc => ({ ...acc, type: 'account' }))

  const results = [
    ...filteredNavigation,
    ...filteredAccounts,
    ...transactions.map(tx => ({ ...tx, type: 'transaction' }))
  ]

  const handleSelect = (result: any) => {
    if (result.type === 'nav') navigate(result.href)
    else if (result.type === 'account') navigate(`/accounts/${result.id}`)
    else if (result.type === 'transaction') navigate(`/accounts/${result.account_id}`)
    setSearchOpen(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setActiveIndex((prev) => (prev + 1) % results.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setActiveIndex((prev) => (prev - 1 + results.length) % results.length)
    } else if (e.key === "Enter") {
      if (results[activeIndex]) {
        handleSelect(results[activeIndex])
      }
    }
  }

  // Scroll active item into view
  useEffect(() => {
    const activeElement = document.getElementById(`result-${activeIndex}`)
    if (activeElement) {
      activeElement.scrollIntoView({ block: 'nearest' })
    }
  }, [activeIndex])

  return (
    <Dialog open={isSearchOpen} onOpenChange={setSearchOpen}>
      <DialogContent 
        className="sm:max-w-[600px] p-0 gap-0 overflow-hidden border-none shadow-2xl rounded-2xl max-sm:left-0 max-sm:top-[var(--vvt,0px)] max-sm:flex max-sm:h-[var(--vvh,100dvh)] max-sm:max-h-none max-sm:w-full max-sm:max-w-none max-sm:translate-x-0 max-sm:translate-y-0 max-sm:flex-col max-sm:rounded-none max-sm:pt-[env(safe-area-inset-top)] max-sm:[&>button:last-child]:top-[calc(1rem+env(safe-area-inset-top))] max-sm:data-[state=closed]:slide-out-to-left-0 max-sm:data-[state=closed]:slide-out-to-top-0 max-sm:data-[state=open]:slide-in-from-left-0 max-sm:data-[state=open]:slide-in-from-top-0"
        style={viewport ? ({ "--vvh": `${viewport.height}px`, "--vvt": `${viewport.top}px` } as React.CSSProperties) : undefined}
        onKeyDown={handleKeyDown}
      >
        <DialogHeader className="px-4 py-3 pr-12 border-b flex flex-row items-center gap-3 shrink-0 sm:py-4 sm:pr-4">
          <Search className="h-5 w-5 text-slate-400 shrink-0" />
          <Input
            placeholder="Rechercher un compte, une vue, un commerçant..."
            className="border-none shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-lg p-0 h-11 sm:h-10"
            inputMode="search"
            enterKeyHint="search"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="none"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActiveIndex(0)
            }}
            autoFocus
          />
          {loading && (
            <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}
        </DialogHeader>
        <ScrollArea className="min-h-0 flex-1 max-sm:[&>[data-radix-scroll-area-viewport]>div]:!block sm:max-h-[450px] sm:flex-none">
          <div className="p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]" ref={scrollRef}>
            {filteredNavigation.length > 0 && (
              <div className="mb-4">
                <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                  Navigation
                </h3>
                {filteredNavigation.map((item, idx) => {
                  const resultIdx = idx
                  const isActive = activeIndex === resultIdx
                  return (
                    <button
                      key={item.href}
                      id={`result-${resultIdx}`}
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setActiveIndex(resultIdx)}
                      className={cn(
                        "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                        isActive ? "bg-slate-100" : "hover:bg-slate-50"
                      )}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <div className={cn(
                          "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center transition-colors",
                          isActive ? "bg-white text-slate-900 shadow-sm" : "bg-slate-100 text-slate-600"
                        )}>
                          <item.icon className="h-4 w-4" />
                        </div>
                        <span className="truncate font-medium text-slate-900">{item.name}</span>
                      </div>
                      <ArrowRight className={cn(
                        "h-4 w-4 text-slate-300 transition-all",
                        isActive ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2"
                      )} />
                    </button>
                  )
                })}
              </div>
            )}

            {filteredAccounts.length > 0 && (
              <div className="mb-4">
                <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                  Comptes
                </h3>
                {filteredAccounts.map((acc, idx) => {
                  const resultIdx = filteredNavigation.length + idx
                  const isActive = activeIndex === resultIdx
                  return (
                    <button
                      key={acc.id}
                      id={`result-${resultIdx}`}
                      onClick={() => handleSelect(acc)}
                      onMouseEnter={() => setActiveIndex(resultIdx)}
                      className={cn(
                        "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                        isActive ? "bg-slate-100" : "hover:bg-slate-50"
                      )}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <div className={cn(
                          "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center font-bold text-[10px] uppercase transition-colors",
                          isActive ? "bg-white text-blue-600 shadow-sm" : "bg-blue-50 text-blue-600"
                        )}>
                          {acc.type.substring(0, 2)}
                        </div>
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate font-medium text-slate-900">{acc.name}</span>
                          <span className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">{acc.type}</span>
                        </div>
                      </div>
                      <Badge variant="outline" className={cn(
                        "shrink-0 whitespace-nowrap text-[10px] border-slate-200 text-slate-500",
                        isActive && "bg-white"
                      )}>
                        {isPrivacyMode ? "****" : formatCurrency(acc.balance, acc.currency)}
                      </Badge>
                    </button>
                  )
                })}
              </div>
            )}

            {transactions.length > 0 && (
              <div className="mb-2">
                <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                  Transactions récentes
                </h3>
                {transactions.map((tx, idx) => {
                  const resultIdx = filteredNavigation.length + filteredAccounts.length + idx
                  const isActive = activeIndex === resultIdx
                  return (
                    <button
                      key={tx.id}
                      id={`result-${resultIdx}`}
                      onClick={() => handleSelect(tx)}
                      onMouseEnter={() => setActiveIndex(resultIdx)}
                      className={cn(
                        "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                        isActive ? "bg-slate-100" : "hover:bg-slate-50"
                      )}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <div className={cn(
                          "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center transition-colors",
                          isActive ? "bg-white text-slate-900 shadow-sm" : "bg-slate-50 text-slate-500"
                        )}>
                          <Receipt className="h-4 w-4" />
                        </div>
                        <div className="flex min-w-0 flex-col">
                          <span className="font-medium text-slate-900 truncate sm:max-w-[300px]">
                            {tx.merchant_obj?.name || tx.merchant}
                          </span>
                          <span className="text-[10px] text-slate-400 flex items-center gap-1.5 truncate">
                            {new Date(tx.date).toLocaleDateString("fr-FR")}
                            {tx.merchant_obj && tx.merchant_obj.name !== tx.merchant && <span className="italic">• {tx.merchant}</span>}
                            {tx.note && <span className="italic">• {tx.note}</span>}
                          </span>
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className={cn(
                          "whitespace-nowrap text-sm font-bold tabular-nums",
                          tx.amount < 0 ? "text-rose-600" : "text-emerald-600"
                        )}>
                          {isPrivacyMode ? "****" : formatCurrency(tx.amount, tx.currency)}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}

            {query && !loading && results.length === 0 && (
              <div className="py-12 text-center">
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-slate-50 mb-3 text-slate-300">
                   <Search className="h-6 w-6" />
                </div>
                <p className="text-slate-500 font-medium">Aucun résultat pour "{query}"</p>
                <p className="text-xs text-slate-400 mt-1">Essayez un autre mot-clé ou vérifiez l'orthographe.</p>
              </div>
            )}
          </div>
        </ScrollArea>
        <div className="hidden shrink-0 px-4 py-3 border-t bg-slate-50 text-[10px] text-slate-400 justify-between items-center sm:flex">
          <div className="flex gap-4">
            <span className="flex items-center gap-1"><kbd className="bg-white border rounded px-1 text-slate-500 font-sans shadow-sm">↑↓</kbd> Naviguer</span>
            <span className="flex items-center gap-1"><kbd className="bg-white border rounded px-1 text-slate-500 font-sans shadow-sm">Enter</kbd> Sélectionner</span>
          </div>
          <div className="flex items-center gap-1">
            <kbd className="bg-white border rounded px-1 text-slate-500 font-sans shadow-sm">ESC</kbd> Fermer
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
