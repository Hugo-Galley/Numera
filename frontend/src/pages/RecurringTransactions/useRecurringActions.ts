import { api } from "@/lib/api"
import { format } from "date-fns"
import { formatCurrency } from "@/lib/utils"
import { fr } from "date-fns/locale"
import { toNaiveLocal } from "@/lib/dates"
import { toast } from "sonner"
import { useEffect } from "react"
import { useSubmit } from "@/hooks/useSubmit"
import { Category, Account, RecurringTransaction } from "./types"
import type { useRecurringState } from "./useRecurringState"
import type { useRecurringForm } from "./useRecurringForm"

/** Chargement et actions : création, modification, suppression, déclenchement, validation des détections. */
export function useRecurringActions(p: ReturnType<typeof useRecurringState> & ReturnType<typeof useRecurringForm>) {
  const { confirm, setRecurringTxs, accounts, setAccounts, categories, setCategories, setSubsData, setSuggestions, setLoading, setIsFormOpen, editingTx, setEditingTx, setIsIrregularSubmenuOpen, setIsManualQuantityOpen, formData, setFormData, showSecurities } = p

  const loadData = async () => {
    setLoading(true)
    try {
      const [txsData, accountsData, categoriesData, sData, suggestionsData] = await Promise.all([
        api.get<RecurringTransaction[]>("/recurring-transactions/"),
        api.get<Account[]>("/accounts"),
        api.get<Category[]>("/categories?include_archived=false"),
        api.get<any>("/analytics/subscriptions?include_other=true"),
        api.get<any>("/analytics/asset-allocation/suggestions")
      ])
      setRecurringTxs(txsData || [])
      setAccounts(accountsData?.filter(a => a) || [])
      setCategories(categoriesData || [])
      setSubsData(sData)
      if (suggestionsData) setSuggestions(suggestionsData)
    } catch (error) {
      console.error("Error loading data:", error)
      toast.error("Erreur lors du chargement des données")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleOpenCreate = () => {
    setEditingTx(null)
    setIsIrregularSubmenuOpen(false)
    setIsManualQuantityOpen(false)
    const firstAccount = accounts[0]
    setFormData({
      account_id: firstAccount?.id.toString() || "",
      name: "",
      type: firstAccount?.type === "investissement" ? "versement" : "Sortie",
      amount: "",
      currency: firstAccount?.currency || "EUR",
      category_id: "none",
      frequency: "monthly",
      day_of_month: "1",
      excluded_months: [],
      start_date: format(new Date(), "yyyy-MM-dd"),
      is_active: true,
      auto_generate: false,
      transfer_to_account_id: "none",
      transfer_credit_day: "",
      note: "",
      asset_class: "",
      sector: "",
      geographic_zone: "",
      ticker: "",
      isin: "",
      quantity: "",
      unit_price: "",
      whole_shares: false,
      etf_profile_id: null,
      logo: null,
    })
    setIsFormOpen(true)
  }

  const handleOpenEdit = (tx: RecurringTransaction) => {
    setEditingTx(tx)
    setIsIrregularSubmenuOpen(Boolean(tx.excluded_months && tx.excluded_months.length > 0))
    setIsManualQuantityOpen(Boolean(tx.quantity && tx.quantity > 0))
    setFormData({
      account_id: tx.account_id.toString(),
      name: tx.name,
      type: tx.type,
      amount: tx.amount.toString(),
      currency: tx.currency,
      category_id: tx.category_id?.toString() || "none",
      frequency: tx.frequency,
      day_of_month: tx.day_of_month?.toString() || "1",
      excluded_months: tx.excluded_months || [],
      start_date: format(new Date(tx.start_date), "yyyy-MM-dd"),
      is_active: tx.is_active,
      auto_generate: tx.auto_generate,
      transfer_to_account_id: tx.transfer_to_account_id?.toString() || "none",
      transfer_credit_day: tx.transfer_credit_day?.toString() || "",
      note: tx.note || "",
      asset_class: tx.asset_class || "",
      sector: tx.sector || "",
      geographic_zone: tx.geographic_zone || "",
      ticker: tx.ticker || "",
      isin: tx.isin || "",
      quantity: tx.quantity != null ? tx.quantity.toString() : "",
      unit_price: tx.unit_price != null ? tx.unit_price.toString() : "",
      whole_shares: Boolean(tx.whole_shares),
      etf_profile_id: tx.etf_profile_id || null,
      logo: tx.logo || null,
    })
    setIsFormOpen(true)
  }

  const [handleSubmit, handleSubmitBusy] = useSubmit(async () => {
    if (!formData.name || !formData.amount || !formData.account_id) {
      toast.error("Veuillez remplir les champs obligatoires")
      return
    }

    const hasTransfer = formData.type === "Sortie" && formData.transfer_to_account_id !== "none"
    const payload = {
      ...formData,
      account_id: parseInt(formData.account_id),
      amount: parseFloat(formData.amount),
      category_id: formData.category_id === "none" ? null : parseInt(formData.category_id),
      transfer_to_account_id: hasTransfer ? parseInt(formData.transfer_to_account_id) : null,
      transfer_credit_day: hasTransfer && formData.transfer_credit_day ? parseInt(formData.transfer_credit_day) : null,
      day_of_month: parseInt(formData.day_of_month),
      excluded_months: formData.frequency === "monthly" && formData.excluded_months.length > 0 ? formData.excluded_months : null,
      start_date: toNaiveLocal(formData.start_date),
      asset_class: formData.asset_class || null,
      sector: formData.sector || null,
      geographic_zone: formData.geographic_zone || null,
      ticker: showSecurities && formData.ticker ? formData.ticker.trim().toUpperCase() : null,
      isin: formData.isin ? formData.isin.trim().toUpperCase() : null,
      quantity: formData.quantity ? parseFloat(formData.quantity) : null,
      unit_price: formData.unit_price ? parseFloat(formData.unit_price) : null,
      whole_shares: Boolean(formData.ticker) && !formData.quantity && formData.whole_shares,
      etf_profile_id: formData.etf_profile_id || null,
      logo: formData.logo || null,
    }

    try {
      if (editingTx) {
        await api.patch(`/recurring-transactions/${editingTx.id}`, payload)
        toast.success("Transaction récurrente mise à jour")
      } else {
        await api.post("/recurring-transactions/", payload)
        toast.success("Transaction récurrente créée")
      }
      setIsFormOpen(false)
      loadData()
    } catch (error) {
      console.error("Error saving recurring tx:", error)
      toast.error("Erreur lors de l'enregistrement")
    }
  })

  const handleDelete = async (id: number) => {
    if (!(await confirm("Êtes-vous sûr de vouloir supprimer cette récurrence ?"))) return
    try {
      await api.delete(`/recurring-transactions/${id}`)
      toast.success("Transaction récurrente supprimée")
      loadData()
    } catch (error) {
      console.error("Error deleting recurring tx:", error)
      toast.error("Erreur lors de la suppression")
    }
  }

  const [handleTrigger, handleTriggerBusy] = useSubmit(async () => {
    try {
      const count = await api.post<number>("/recurring-transactions/trigger", {})
      toast.success(`${count} transaction(s) générée(s)`)
      loadData()
    } catch (error) {
      console.error("Error triggering generation:", error)
      toast.error("Erreur lors de la génération")
    }
  })

  const toggleActive = async (tx: RecurringTransaction) => {
    try {
      await api.patch(`/recurring-transactions/${tx.id}`, { is_active: !tx.is_active })
      loadData()
    } catch (error) {
      toast.error("Erreur lors de la modification")
    }
  }

  const handleOpenValidate = (potential: any, isInvest: boolean = false) => {
    setEditingTx(null)
    setIsIrregularSubmenuOpen(false)
    let acc = accounts[0]
    if (isInvest) {
      const invAcc = accounts.find(a => a.type === "investissement")
      if (invAcc) acc = invAcc
    }

    setFormData({
      account_id: acc?.id.toString() || "",
      name: potential.name,
      type: isInvest ? "versement" : "Sortie",
      amount: potential.amount.toString(),
      currency: acc?.currency || "EUR",
      category_id: categories.find(c => c.name === potential.category_name)?.id.toString() || "none",
      frequency: "monthly",
      day_of_month: "1",
      excluded_months: [],
      start_date: format(new Date(), "yyyy-MM-dd"),
      is_active: true,
      auto_generate: false,
      transfer_to_account_id: "none",
      transfer_credit_day: "",
      note: isInvest ? "Validé comme investissement" : "Validé depuis détection automatique",
      asset_class: "",
      sector: "",
      geographic_zone: "",
      ticker: "",
      isin: "",
      quantity: "",
      unit_price: "",
      whole_shares: false,
      etf_profile_id: null,
      logo: null,
    })
    setIsFormOpen(true)
  }

  const handleIgnoreDetection = async (potential: any) => {
    if (!(await confirm(`Ne plus suggérer "${potential.name}" (${formatCurrency(potential.amount)}) comme abonnement ?`, { title: "Ignorer la suggestion", confirmLabel: "Ne plus suggérer", destructive: false }))) return
    try {
      await api.post("/analytics/subscriptions/ignore", {
        merchant: potential.name,
        amount: potential.amount
      })
      toast.success("Suggestion ignorée")
      loadData()
    } catch (error) {
      console.error("Error ignoring detection:", error)
      toast.error("Erreur lors de l'opération")
    }
  }

  const safeFormat = (dateStr: string | null | undefined, formatStr: string) => {
    if (!dateStr) return "-"
    try {
      const d = new Date(dateStr)
      if (isNaN(d.getTime())) return "-"
      return format(d, formatStr, { locale: fr })
    } catch (e) {
      return "-"
    }
  }
  return { loadData, handleOpenCreate, handleOpenEdit, handleSubmit, handleSubmitBusy, handleDelete, handleTrigger, handleTriggerBusy, toggleActive, handleOpenValidate, handleIgnoreDetection, safeFormat }
}
