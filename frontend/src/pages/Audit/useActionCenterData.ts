import { api } from "@/lib/api"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Account, ActionCenterData, ActionItem, Category, IssueDetails, Transaction } from "./types"

/** Chargement du Centre d'actions, détail d'un problème et actions (masquer, rapprocher, ignorer). */
export function useActionCenterData() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  // ?vue=virements : revue des virements internes (suggestions à lier, virements déjà liés)
  const view = searchParams.get("vue")
  const [data, setData] = useState<ActionCenterData | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [details, setDetails] = useState<Record<string, IssueDetails>>({})
  const [activeActionId, setActiveActionId] = useState<string | null>(null)
  const [ruleMerchant, setRuleMerchant] = useState<{merchant: string, catId?: number} | null>(null)
  const [normMerchant, setNormMerchant] = useState<{ merchant: string; variants?: string[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingIssueId, setLoadingIssueId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadActions() {
    setLoading(true)
    setError(null)
    try {
      const [result, categoryRows, accountRows] = await Promise.all([
        api.get<ActionCenterData>("/analytics/actions"),
        api.get<Category[]>("/categories?include_archived=false"),
        api.get<Account[]>("/accounts"),
      ])
      setData(result)
      setCategories(categoryRows || [])
      setAccounts(accountRows || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Données indisponibles")
    } finally {
      setLoading(false)
    }
  }

  async function dismissAction(e: React.MouseEvent, actionId: string) {
    e.stopPropagation()
    try {
      await api.post('/analytics/actions/dismiss', { id: actionId })
      setData(prev => prev ? {
        ...prev,
        actions: prev.actions.filter(a => a.id !== actionId)
      } : null)
      toast.success("Action masquée")
    } catch(err) {
      toast.error("Impossible de masquer l'action")
    }
  }

  async function handleAction(action: ActionItem) {
    if (action.action_type === "link" && action.action_url) {
      navigate(action.action_url)
      return
    }

    if (action.action_type === "modal_rule") {
      setRuleMerchant({ merchant: action.metadata?.merchant, catId: action.metadata?.suggested_category_id })
      return
    }

    if (action.action_type === "modal_merchant") {
      setNormMerchant({ merchant: action.metadata?.merchant, variants: action.metadata?.variants })
      return
    }

    if (action.action_type === "modal_categorize") {
      const issueId = action.metadata?.issue_id
      if (!issueId) return
      
      setActiveActionId(action.id)
      if (details[issueId]) return

      setLoadingIssueId(action.id)
      try {
        const result = await api.get<IssueDetails>(`/analytics/audit/${issueId}`)
        setDetails((prev) => ({ ...prev, [issueId]: result }))
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Chargement impossible")
      } finally {
        setLoadingIssueId(null)
      }
    }
  }

  const activeAction = data?.actions.find(a => a.id === activeActionId)
  const activeIssueId = activeAction?.metadata?.issue_id
  const detail = activeIssueId ? details[activeIssueId] : null

  async function refreshIssue(issueId: string) {
    const result = await api.get<IssueDetails>(`/analytics/audit/${issueId}`)
    setDetails((prev) => ({ ...prev, [issueId]: result }))
    await loadActions()
  }

  function updateTransactionInDetails(issueId: string, saved: Transaction) {
    setDetails((prev) => {
      const detail = prev[issueId]
      if (!detail) return prev
      return {
        ...prev,
        [issueId]: {
          ...detail,
          transactions: detail.transactions?.map((tx) => tx.id === saved.id ? saved : tx),
          duplicate_groups: detail.duplicate_groups?.map((group) => ({
            ...group,
            transactions: group.transactions.map((tx) => tx.id === saved.id ? saved : tx),
          })),
          transfer_pairs: detail.transfer_pairs?.map((pair) => ({
            sortie: pair.sortie.id === saved.id ? saved : pair.sortie,
            entree: pair.entree.id === saved.id ? saved : pair.entree,
          })),
        },
      }
    })
    loadActions()
  }

  function removeTransactionFromDetails(issueId: string, id: number) {
    setDetails((prev) => {
      const detail = prev[issueId]
      if (!detail) return prev
      return {
        ...prev,
        [issueId]: {
          ...detail,
          transactions: detail.transactions?.filter((tx) => tx.id !== id),
          duplicate_groups: detail.duplicate_groups
            ?.map((group) => ({ ...group, transactions: group.transactions.filter((tx) => tx.id !== id) }))
            .filter((group) => group.transactions.length > 1),
          transfer_pairs: detail.transfer_pairs?.filter((pair) => pair.sortie.id !== id && pair.entree.id !== id),
        },
      }
    })
    loadActions()
  }

  async function linkTransfer(sortieId: number, entreeId: number) {
    try {
      await api.post(`/transactions/${sortieId}/link/${entreeId}?type=regular`, {})
      toast.success("Transfert rapproché")
      if (activeIssueId) await refreshIssue(activeIssueId)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Rapprochement impossible")
    }
  }

  async function ignoreTransfer(sortieId: number) {
    try {
      await api.post(`/transactions/${sortieId}/ignore`, {})
      toast.success("Suggestion ignorée")
      if (activeIssueId) await refreshIssue(activeIssueId)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action impossible")
    }
  }

  async function ignoreDuplicate(transactions: Transaction[]) {
    try {
      await Promise.all(transactions.map((tx) => api.post(`/transactions/${tx.id}/ignore-duplicate`, {})))
      toast.success("Doublons ignorés")
      if (activeIssueId) await refreshIssue(activeIssueId)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action impossible")
    }
  }

  useEffect(() => {
    if (!view) loadActions()
  }, [view])
  return { navigate, searchParams, view, data, setData, categories, setCategories, accounts, setAccounts, details, setDetails, activeActionId, setActiveActionId, ruleMerchant, setRuleMerchant, normMerchant, setNormMerchant, loading, setLoading, loadingIssueId, setLoadingIssueId, error, setError, loadActions, dismissAction, handleAction, activeAction, activeIssueId, detail, refreshIssue, updateTransactionInDetails, removeTransactionFromDetails, linkTransfer, ignoreTransfer, ignoreDuplicate }
}
