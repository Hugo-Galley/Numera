import { Landmark, PiggyBank, Shield, TrendingUp, Wallet } from "lucide-react"
import { accountTypeLabel } from "@/lib/labels"
import { api } from "@/lib/api"
import { invalidateAccountLogos } from "@/components/ui/AccountLogo"
import { toast } from "sonner"
import { useEffect, useMemo } from "react"
import { useSubmit } from "@/hooks/useSubmit"
import { Account } from "./types"
import type { useAccountsState } from "./useAccountsState"

/** Chargement, tri et actions sur les comptes (création, modification, archivage, compte principal). */
export function useAccountsActions(p: ReturnType<typeof useAccountsState>) {
  const { accounts, setAccounts, setLoading, setIsDialogOpen, setIsEditDialogOpen, editingAccount, setEditingAccount, newName, setNewName, newType, newCurrency, setNewCurrency, newInstitution, setNewInstitution, newLogo, setNewLogo, newAssetClass, setNewAssetClass, newSector, setNewSector, newZone, setNewZone, newValuationMode, setNewValuationMode, newTaxWrapper, setNewTaxWrapper, newOpenedAt, setNewOpenedAt, newEurosPct, setNewEurosPct, newInvestisPct, setNewInvestisPct, sortField, setSortField, sortOrder, setSortOrder, setSuggestions, confirm, setArchivedAccounts } = p
  const loadAccounts = async () => {
    setLoading(true)
    try {
      const data = await api.get<Account[]>("/accounts")
      if (data && Array.isArray(data)) {
        setAccounts(data.filter((account) => account && account.active))
        setArchivedAccounts(data.filter((account) => account && !account.active))
      } else {
        setAccounts([])
      }
    } catch (error) {
      console.error("Error loading accounts:", error)
      toast.error("Erreur lors du chargement des comptes")
      setAccounts([])
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    try {
      const data = await api.get<any>("/analytics/asset-allocation/suggestions")
      if (data) setSuggestions(data)
    } catch (error) {
      console.error("Error loading suggestions:", error)
      toast.error("Impossible de charger les suggestions d'allocation")
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

  useEffect(() => {
    loadAccounts()
    loadSuggestions()
  }, [])

  const [handleCreateAccount, handleCreateAccountBusy] = useSubmit(async () => {
    if (!newName.trim()) {
      toast.error("Le nom du compte est requis")
      return
    }
    try {
      await api.post("/accounts", { 
        name: newName, 
        type: newType, 
        currency: newCurrency,
        institution: newInstitution || null,
        logo: newLogo,
        asset_class: newType === "investissement" ? newAssetClass : null,
        sector: newType === "investissement" ? newSector : null,
        geographic_zone: newType === "investissement" ? newZone : null,
        valuation_mode: newType === "investissement" || newType === "assurance_vie" ? newValuationMode : "positions",
        tax_wrapper: newTaxWrapper === "none" ? null : newTaxWrapper,
        opened_at: newTaxWrapper === "none" || !newOpenedAt ? null : newOpenedAt,
        fonds_euros_pct: newType === "assurance_vie" ? (newEurosPct ? parseFloat(newEurosPct) : 0) : null,
        fonds_investis_pct: newType === "assurance_vie" ? (newInvestisPct ? parseFloat(newInvestisPct) : 0) : null
      })
      invalidateAccountLogos()
      toast.success("Compte créé avec succès")
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
    } catch (error) {
      toast.error("Erreur lors de la création du compte")
    }
  })

  const [handleUpdateAccount, handleUpdateAccountBusy] = useSubmit(async () => {
    if (!editingAccount) return
    try {
      await api.patch(`/accounts/${editingAccount.id}`, { 
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
      await Promise.all(siblings.map((x) => api.patch(`/accounts/${x.id}`, { logo: editingAccount.logo })))
      invalidateAccountLogos()
      toast.success(siblings.length ? `Compte mis à jour (logo appliqué à ${siblings.length} autre(s) compte(s))` : "Compte mis à jour")
      setIsEditDialogOpen(false)
      setEditingAccount(null)
      loadAccounts()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour")
    }
  })

  // DELETE /accounts/{id} archive le compte (active = false) : l'historique reste dans les analyses passées
  const handleDeleteAccount = async (accountId: number) => {
    if (!(await confirm("Archiver ce compte ? Il disparaît des listes et du patrimoine ; son historique est conservé et vous pourrez le réactiver."))) return
    try {
      await api.delete(`/accounts/${accountId}`)
      toast.success("Compte archivé")
      loadAccounts()
    } catch (error) {
      toast.error("Erreur lors de l'archivage du compte")
    }
  }

  const handleRestoreAccount = async (accountId: number) => {
    try {
      await api.patch(`/accounts/${accountId}`, { active: true })
      toast.success("Compte réactivé")
      loadAccounts()
    } catch (error) {
      toast.error("Erreur lors de la réactivation du compte")
    }
  }

  const handleToggleMain = async (accountId: number, currentIsMain: boolean) => {
    try {
      await api.patch(`/accounts/${accountId}`, { is_main: !currentIsMain })
      toast.success(currentIsMain ? "Compte retiré des favoris" : "Compte défini comme principal")
      loadAccounts()
    } catch (error) {
      toast.error("Erreur lors de la modification")
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
