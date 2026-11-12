import { Landmark, PiggyBank, Shield, TrendingUp, Wallet } from "lucide-react"
import { accountTypeLabel } from "@/lib/labels"
import { invalidateAccountLogos } from "@/components/ui/AccountLogo"
import i18n from "i18next"
import { toast } from "sonner"
import { useEffect, useEffectEvent, useMemo } from "react"
import { useSubmit } from "@/hooks/useSubmit"
import { Account } from "./types"
import type { useAccountsState } from "./useAccountsState"
import { deleteAccountsById, getAccounts, patchAccountsById, postAccounts } from "@/lib/api/accounts"
import { getAnalyticsAssetAllocationSuggestions } from "@/lib/api/analytics"
import type { ApiBody } from "@/lib/api/types"

type NewAccount = ApiBody<"/accounts", "post">

/** Chargement, tri et actions sur les comptes (création, modification, archivage, compte principal). */
export function useAccountsActions(p: ReturnType<typeof useAccountsState>) {
  const { accounts, setAccounts, setLoading, setIsDialogOpen, setIsEditDialogOpen, editingAccount, setEditingAccount, newName, setNewName, newType, newCurrency, setNewCurrency, newInstitution, setNewInstitution, newLogo, setNewLogo, newAssetClass, setNewAssetClass, newSector, setNewSector, newZone, setNewZone, newValuationMode, setNewValuationMode, newTaxWrapper, setNewTaxWrapper, newOpenedAt, setNewOpenedAt, newEurosPct, setNewEurosPct, newInvestisPct, setNewInvestisPct, sortField, setSortField, sortOrder, setSortOrder, setSuggestions, confirm, setArchivedAccounts } = p
  const loadAccounts = async () => {
    setLoading(true)
    try {
      const data = await getAccounts<Account[]>()
      if (data && Array.isArray(data)) {
        setAccounts(data.filter((account) => account && account.active))
        setArchivedAccounts(data.filter((account) => account && !account.active))
      } else {
        setAccounts([])
      }
    } catch (error) {
      console.error("Error loading accounts:", error)
      toast.error(i18n.t("toast.loadError", { ns: "accounts" }))
      setAccounts([])
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    try {
      const data = await getAnalyticsAssetAllocationSuggestions()
      if (data) setSuggestions(data)
    } catch (error) {
      console.error("Error loading suggestions:", error)
      toast.error(i18n.t("toast.suggestionsError", { ns: "accounts" }))
    }
  }

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortOrder("asc")
    }
  }

  const sortedAccounts = useMemo(() => {
    if (!accounts || !Array.isArray(accounts)) return []
    return [...accounts].sort((a, b) => {
      if (!a || !b) return 0
      // Le compte principal (étoile) reste en tête, quel que soit le tri
      if (!!a.is_main !== !!b.is_main) return a.is_main ? -1 : 1
      let comparison = 0
      switch (sortField) {
        case "name":
          comparison = (a.name || "").localeCompare(b.name || "")
          break
        case "type":
          comparison = (a.type || "").localeCompare(b.type || "")
          break
        case "currency":
          comparison = (a.currency || "").localeCompare(b.currency || "")
          break
        case "institution":
          comparison = (a.institution || "").localeCompare(b.institution || "")
          break
      }
      return sortOrder === "asc" ? comparison : -comparison
    })
  }, [accounts, sortField, sortOrder])

  const loadOnMount = useEffectEvent(() => {
    loadAccounts()
    loadSuggestions()
  })
  useEffect(() => {
    loadOnMount()
  }, [])

  const [handleCreateAccount, handleCreateAccountBusy] = useSubmit(async () => {
    if (!newName.trim()) {
      toast.error(i18n.t("toast.nameRequired", { ns: "accounts" }))
      return
    }
    try {
      await postAccounts({ 
        name: newName, 
        type: newType as NewAccount["type"],
        currency: newCurrency,
        institution: newInstitution || null,
        logo: newLogo,
        asset_class: newType === "investissement" ? newAssetClass : null,
        sector: newType === "investissement" ? newSector : null,
        geographic_zone: newType === "investissement" ? newZone : null,
        valuation_mode: newType === "investissement" || newType === "assurance_vie" ? newValuationMode : "positions",
        tax_wrapper: newTaxWrapper === "none" ? null : (newTaxWrapper as NewAccount["tax_wrapper"]),
        opened_at: newTaxWrapper === "none" || !newOpenedAt ? null : newOpenedAt,
        fonds_euros_pct: newType === "assurance_vie" ? (newEurosPct ? parseFloat(newEurosPct) : 0) : null,
        fonds_investis_pct: newType === "assurance_vie" ? (newInvestisPct ? parseFloat(newInvestisPct) : 0) : null
      })
      invalidateAccountLogos()
      toast.success(i18n.t("toast.created", { ns: "accounts" }))
      setIsDialogOpen(false)
      setNewName("")
      setNewCurrency("EUR")
      setNewInstitution("")
      setNewLogo(null)
      setNewAssetClass("")
      setNewSector("")
      setNewZone("")
      setNewValuationMode("positions")
      setNewTaxWrapper("none")
      setNewOpenedAt("")
      setNewEurosPct("")
      setNewInvestisPct("")
      loadAccounts()
    } catch {
      toast.error(i18n.t("toast.createError", { ns: "accounts" }))
    }
  })

  const [handleUpdateAccount, handleUpdateAccountBusy] = useSubmit(async () => {
    // Un compte crédit se modifie avec son prêt : l'API des comptes refuse le type `credit`
    if (!editingAccount || editingAccount.type === "credit") return
    try {
      await patchAccountsById(editingAccount.id, {
        name: editingAccount.name, 
        type: editingAccount.type, 
        currency: editingAccount.currency,
        institution: editingAccount.institution || null,
        logo: editingAccount.logo || null,
        asset_class: editingAccount.type === "investissement" ? editingAccount.asset_class : null,
        sector: editingAccount.type === "investissement" ? editingAccount.sector : null,
        geographic_zone: editingAccount.type === "investissement" ? editingAccount.geographic_zone : null,
        valuation_mode: editingAccount.type === "investissement" || editingAccount.type === "assurance_vie" ? (editingAccount.valuation_mode ?? (editingAccount.type === "assurance_vie" ? "snapshot" : "positions")) : "positions",
        tax_wrapper: editingAccount.tax_wrapper ?? null,
        opened_at: editingAccount.tax_wrapper ? (editingAccount.opened_at || null) : null,
        fonds_euros_pct: editingAccount.type === "assurance_vie" ? (editingAccount.fonds_euros_pct !== undefined && editingAccount.fonds_euros_pct !== null ? editingAccount.fonds_euros_pct : 0) : null,
        fonds_investis_pct: editingAccount.type === "assurance_vie" ? (editingAccount.fonds_investis_pct !== undefined && editingAccount.fonds_investis_pct !== null ? editingAccount.fonds_investis_pct : 0) : null
      })
      // Même banque : on applique le logo aux autres comptes qui n'en ont pas encore.
      const inst = editingAccount.institution?.trim().toLowerCase()
      const siblings = editingAccount.logo && inst
        ? accounts.filter((x) => x.id !== editingAccount.id && !x.logo && x.institution?.trim().toLowerCase() === inst)
        : []
      await Promise.all(siblings.map((x) => patchAccountsById(x.id, { logo: editingAccount.logo })))
      invalidateAccountLogos()
      toast.success(siblings.length ? i18n.t("toast.updatedWithLogo", { ns: "accounts", count: siblings.length }) : i18n.t("toast.updated", { ns: "accounts" }))
      setIsEditDialogOpen(false)
      setEditingAccount(null)
      loadAccounts()
    } catch {
      toast.error(i18n.t("toast.updateError", { ns: "accounts" }))
    }
  })

  // DELETE /accounts/{id} archive le compte (active = false) : l'historique reste dans les analyses passées
  const handleDeleteAccount = async (accountId: number) => {
    if (!(await confirm(i18n.t("toast.confirmArchive", { ns: "accounts" })))) return
    try {
      await deleteAccountsById(accountId)
      toast.success(i18n.t("toast.archived", { ns: "accounts" }))
      loadAccounts()
    } catch {
      toast.error(i18n.t("toast.archiveError", { ns: "accounts" }))
    }
  }

  const handleRestoreAccount = async (accountId: number) => {
    try {
      await patchAccountsById(accountId, { active: true })
      toast.success(i18n.t("toast.restored", { ns: "accounts" }))
      loadAccounts()
    } catch {
      toast.error(i18n.t("toast.restoreError", { ns: "accounts" }))
    }
  }

  const handleToggleMain = async (accountId: number, currentIsMain: boolean) => {
    try {
      await patchAccountsById(accountId, { is_main: !currentIsMain })
      toast.success(currentIsMain ? i18n.t("toast.mainRemoved", { ns: "accounts" }) : i18n.t("toast.mainSet", { ns: "accounts" }))
      loadAccounts()
    } catch {
      toast.error(i18n.t("toast.mainError", { ns: "accounts" }))
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "courant": return <Wallet className="h-4 w-4" />
      case "epargne": return <PiggyBank className="h-4 w-4" />
      case "investissement": return <TrendingUp className="h-4 w-4" />
      case "assurance_vie": return <Shield className="h-4 w-4" />
      case "credit": return <Landmark className="h-4 w-4" />
      default: return <Wallet className="h-4 w-4" />
    }
  }

  const getTypeLabel = accountTypeLabel

  const CURRENCIES = ["EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD"]

  return { loadAccounts, loadSuggestions, handleSort, sortedAccounts, handleCreateAccount, handleCreateAccountBusy, handleUpdateAccount, handleUpdateAccountBusy, handleDeleteAccount, handleRestoreAccount, handleToggleMain, getTypeIcon, getTypeLabel, CURRENCIES }
}
