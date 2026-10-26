import React, { useState, useEffect, useRef } from "react"
import { accountTypeLabel } from "@/lib/labels"
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
  Bell,
  Plus,
  Zap,
  EyeOff,
  Landmark as LandmarkIcon,
  ClipboardList,
} from "lucide-react"
import { toast } from "sonner"
import { parseQuickEntry } from "@/lib/quickEntry"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
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
  { name: "Notifications (ntfy, Telegram)", href: "/settings?tab=notifications", icon: Bell },
  { name: "Paramètres", href: "/settings", icon: Settings },
]

export function Omnibox() {
  const navigate = useNavigate()
  const { isSearchOpen, setSearchOpen, isPrivacyMode, togglePrivacyMode } = useUI()
  const [query, setQuery] = useState("")
  const [accounts, setAccounts] = useState<any[]>([])
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [searchFailed, setSearchFailed] = useState(false)
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
      setLoading(false)  // sinon le spinner d'une recherche interrompue restait affiché
      setSearchFailed(false)
      return
    }

    let isCurrent = true
    const timer = setTimeout(async () => {
      try {
        setLoading(true)
        setSearchFailed(false)
        const data = await api.get<any[]>(`/transactions?search=${encodeURIComponent(query)}&limit=10`)
        if (isCurrent) {
          setTransactions(data || [])
          setActiveIndex(0)
        }
      } catch (error) {
        if (isCurrent) {
          console.error("Failed to search transactions", error)
          setTransactions([])
          setSearchFailed(true)
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

  // `type` sert au routage des résultats : le sens de la transaction (Entree, Sortie…) est gardé dans `txType`
  const asTransactionResult = (tx: any) => ({ ...tx, type: 'transaction', txType: tx.type })

  const filteredNavigation = NAVIGATION.filter((item) =>
    item.name.toLowerCase().includes(query.toLowerCase())
  ).map(item => ({ ...item, type: 'nav' }))

  const filteredAccounts = accounts.filter((acc) =>
    acc.name.toLowerCase().includes(query.toLowerCase())
  ).map(acc => ({ ...acc, type: 'account' }))

  // Compte des saisies rapides : compte principal, sinon premier compte courant actif
  const mainAccount = accounts.find((a) => a.active && a.is_main) ?? accounts.find((a) => a.active && a.type === "courant")
  const quickEntry = parseQuickEntry(query)
  const quickResults = quickEntry
    ? [{ amount: quickEntry.amount, merchant: quickEntry.merchant, entryType: quickEntry.type, type: 'quick' }]
    : []

  const ACTIONS = [
    { id: "new-tx", name: "Nouvelle transaction", hint: mainAccount?.name, icon: Plus, run: () => openNewTransaction() },
    { id: "import", name: "Importer un relevé CSV", icon: Upload, run: () => navigate("/settings?tab=import") },
    { id: "review", name: "Démarrer la revue du mois", icon: ClipboardList, run: () => navigate("/month/revue") },
    { id: "privacy", name: isPrivacyMode ? "Afficher les montants" : "Masquer les montants (mode confidentialité)", icon: EyeOff, run: () => togglePrivacyMode() },
    { id: "loan", name: "Ajouter un crédit", icon: LandmarkIcon, run: () => navigate("/accounts?new=loan") },
  ]
  const filteredActions = ACTIONS.filter((action) =>
    action.name.toLowerCase().includes(query.toLowerCase())
  ).map(action => ({ ...action, type: 'action' }))

  const results = [
    ...filteredNavigation,
    ...filteredAccounts,
    ...quickResults,
    ...filteredActions,
    ...transactions.map(asTransactionResult)
  ]

  function openNewTransaction(params: Record<string, string> = {}) {
    if (!mainAccount) {
      toast.error("Aucun compte courant actif pour enregistrer la transaction")
      return
    }
    navigate(`/accounts/${mainAccount.id}?${new URLSearchParams({ new: "tx", ...params }).toString()}`)
  }

  const handleSelect = (result: any) => {
    if (result.type === 'nav') navigate(result.href)
    else if (result.type === 'account') navigate(`/accounts/${result.id}`)
    // La transaction s'ouvre directement en modification dans son compte
    else if (result.type === 'transaction') {
      const { txType, ...tx } = result
      navigate(`/accounts/${result.account_id}`, { state: { openTransaction: { ...tx, type: txType } } })
    }
    else if (result.type === 'action') result.run()
    else if (result.type === 'quick') {
      openNewTransaction({ type: result.entryType, amount: String(result.amount), merchant: result.merchant })
    }
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
          <DialogTitle className="sr-only">Recherche</DialogTitle>
          <DialogDescription className="sr-only">Rechercher un compte, une vue ou une transaction</DialogDescription>
          <Search className="h-5 w-5 text-slate-400 shrink-0" />
          <Input
            placeholder="Rechercher, ou saisir « 12,50 boulangerie »…"
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
                          <span className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">{accountTypeLabel(acc.type)}</span>
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

            {quickResults.length > 0 && (
              <div className="mb-4">
                <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                  Saisie rapide
                </h3>
                {quickResults.map((entry) => {
                  const resultIdx = filteredNavigation.length + filteredAccounts.length
                  const isActive = activeIndex === resultIdx
                  const isIncome = entry.entryType === "Entree"
                  return (
                    <button
                      key="quick-entry"
                      id={`result-${resultIdx}`}
                      onClick={() => handleSelect(entry)}
                      onMouseEnter={() => setActiveIndex(resultIdx)}
                      className={cn(
                        "group w-full flex min-h-12 items-center justify-between gap-2 px-3 py-2 rounded-xl transition-colors text-left outline-none",
                        isActive ? "bg-slate-100" : "hover:bg-slate-50"
                      )}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <div className={cn(
                          "h-8 w-8 shrink-0 rounded-lg flex items-center justify-center transition-colors",
                          isIncome ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"
                        )}>
                          <Zap className="h-4 w-4" />
                        </div>
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate font-medium text-slate-900">
                            {isIncome ? "Ajouter un revenu" : "Ajouter une dépense"} de {formatCurrency(entry.amount)}
                            {entry.merchant && <> · {entry.merchant}</>}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {mainAccount ? `Sur ${mainAccount.name}, à vérifier avant d'enregistrer` : "Aucun compte courant actif"}
                          </span>
                        </div>
                      </div>
                      <ArrowRight className={cn("h-4 w-4 text-slate-300 transition-all", isActive ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2")} />
                    </button>
                  )
                })}
              </div>
            )}

            {filteredActions.length > 0 && (
              <div className="mb-4">
                <h3 className="px-3 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                  Actions
                </h3>
                {filteredActions.map((action, idx) => {
                  const resultIdx = filteredNavigation.length + filteredAccounts.length + quickResults.length + idx
                  const isActive = activeIndex === resultIdx
                  return (
                    <button
                      key={action.id}
                      id={`result-${resultIdx}`}
                      onClick={() => handleSelect(action)}
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
                          <action.icon className="h-4 w-4" />
                        </div>
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate font-medium text-slate-900">{action.name}</span>
                          {action.hint && <span className="text-[10px] text-slate-400">{action.hint}</span>}
                        </div>
                      </div>
                      <ArrowRight className={cn("h-4 w-4 text-slate-300 transition-all", isActive ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2")} />
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
                  const resultIdx = filteredNavigation.length + filteredAccounts.length + quickResults.length + filteredActions.length + idx
                  const isActive = activeIndex === resultIdx
                  return (
                    <button
                      key={tx.id}
                      id={`result-${resultIdx}`}
                      onClick={() => handleSelect(asTransactionResult(tx))}
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
                        {/* Le montant est toujours positif en base : le sens vient du type */}
                        <span className={cn(
                          "whitespace-nowrap text-sm font-bold tabular-nums",
                          tx.type === "Sortie" ? "text-rose-600" : tx.type === "Solde Initial" ? "text-slate-600" : "text-emerald-600"
                        )}>
                          {isPrivacyMode ? "****" : `${tx.type === "Sortie" ? "- " : tx.type === "Solde Initial" ? "" : "+ "}${formatCurrency(tx.amount, tx.currency)}`}
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
                <p className="text-slate-500 font-medium">{searchFailed ? "La recherche est momentanément indisponible." : `Aucun résultat pour "${query}"`}</p>
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
