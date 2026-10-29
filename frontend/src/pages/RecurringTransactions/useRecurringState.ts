import { safeStorage } from "@/lib/storage"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useSearchParams } from "react-router-dom"
import { useState } from "react"
import { Category, Account, RecurringTransaction } from "./types"

/** État de la page : données, vue, onglet actif (URL ?tab=) et dialogues. */
export function useRecurringState() {
  const confirm = useConfirm()
  const [recurringTxs, setRecurringTxs] = useState<RecurringTransaction[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [subsData, setSubsData] = useState<any>(null)
  const [suggestions, setSuggestions] = useState<{
    asset_classes: string[],
    sectors: string[],
    geographic_zones: string[]
  }>({ asset_classes: [], sectors: [], geographic_zones: [] })
  const [loading, setLoading] = useState(true)
  // Les deux vues se recoupent : on n'en affiche qu'une (réglage mémorisé dans le navigateur)
  const [recurringView, setRecurringView] = useState<"analysis" | "list">(() => {
    try { return safeStorage.getItem("recurring-view") === "list" ? "list" : "analysis" } catch { return "analysis" }
  })
  const changeRecurringView = (view: "analysis" | "list") => {
    setRecurringView(view)
    try { safeStorage.setItem("recurring-view", view) } catch { /* stockage indisponible */ }
  }
  // L'onglet actif vit dans l'URL (?tab=) : les raccourcis (Omnibox, ancienne adresse /calendar)
  // changent d'onglet même quand la page est déjà ouverte
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedTab = searchParams.get("tab")
  const mainTab = recurringView === "list" ? "recurring" : "subscriptions"
  const activeTab = requestedTab === "salary" || requestedTab === "calendar"
    ? requestedTab
    : mainTab
  const setActiveTab = (tab: string) => {
    setSearchParams((params) => {
      params.set("tab", tab)
      return params
    }, { replace: true })
  }
  const [subTab, setSubTab] = useState<"subscriptions" | "investments" | "other">("subscriptions")
  const [flowSub, setFlowSub] = useState<any>(null)
  // Dialogs
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingTx, setEditingTx] = useState<RecurringTransaction | null>(null)
  const [isIrregularSubmenuOpen, setIsIrregularSubmenuOpen] = useState(false)
  const [isManualQuantityOpen, setIsManualQuantityOpen] = useState(false)

  return { confirm, recurringTxs, setRecurringTxs, accounts, setAccounts, categories, setCategories, subsData, setSubsData, suggestions, setSuggestions, loading, setLoading, recurringView, setRecurringView, changeRecurringView, searchParams, setSearchParams, requestedTab, mainTab, activeTab, setActiveTab, subTab, setSubTab, flowSub, setFlowSub, isFormOpen, setIsFormOpen, editingTx, setEditingTx, isIrregularSubmenuOpen, setIsIrregularSubmenuOpen, isManualQuantityOpen, setIsManualQuantityOpen }
}
