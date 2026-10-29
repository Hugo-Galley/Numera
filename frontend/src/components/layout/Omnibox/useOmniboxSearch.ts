import { ClipboardList, EyeOff, Landmark as LandmarkIcon, Plus, Upload } from "lucide-react"
import React, { useEffect, useRef, useState } from "react"
import { parseQuickEntry } from "@/lib/quickEntry"
import { toast } from "sonner"
import { useNavigate } from "react-router-dom"
import { useUI } from "@/providers/UIProvider"
import { NAVIGATION } from "./types"
import { getAccounts } from "@/lib/api/accounts"
import { getTransactions } from "@/lib/api/transactions"

/** Recherche (comptes, transactions, saisie rapide), résultats et navigation clavier. */
export function useOmniboxSearch() {
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
        const data = await getTransactions<any[]>(`?search=${encodeURIComponent(query)}&limit=10`)
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
      const data = await getAccounts<any[]>()
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
    { id: "import", name: "Importer un relevé CSV", icon: Upload, run: () => navigate("/accounts?import=1") },
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

  return { navigate, isSearchOpen, setSearchOpen, isPrivacyMode, togglePrivacyMode, query, setQuery, accounts, setAccounts, transactions, setTransactions, loading, setLoading, searchFailed, setSearchFailed, activeIndex, setActiveIndex, scrollRef, viewport, setViewport, loadAccounts, asTransactionResult, filteredNavigation, filteredAccounts, mainAccount, quickEntry, quickResults, ACTIONS, filteredActions, results, openNewTransaction, handleSelect, handleKeyDown }
}
