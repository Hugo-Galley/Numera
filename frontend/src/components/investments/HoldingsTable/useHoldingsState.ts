import { PortfolioHolding } from "@/types/diversity"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useMemo, useState } from "react"
import { useUI } from "@/providers/UIProvider"
import { HoldingsTableProps, PerfFilter, TypeFilter } from "./types"

/** Filtres, édition du prix de revient et actions sur les positions (décomposer, supprimer, dividendes). */
export function useHoldingsState(p: { accountId: HoldingsTableProps["accountId"]; accountName: HoldingsTableProps["accountName"]; holdings: HoldingsTableProps["holdings"]; onRefresh: HoldingsTableProps["onRefresh"]; onAddDividend: HoldingsTableProps["onAddDividend"] }) {
  const { accountId, accountName, holdings, onRefresh, onAddDividend } = p
  const confirm = useConfirm()
  const [pointZeroOpen, setPointZeroOpen] = useState(false)
  const [costEstimateOpen, setCostEstimateOpen] = useState(false)
  const [editingCostId, setEditingCostId] = useState<number | null>(null)
  const [costDraft, setCostDraft] = useState("")
  const [decomposingId, setDecomposingId] = useState<number | null>(null)
  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all")
  const [perfFilter, setPerfFilter] = useState<PerfFilter>("all")
  // Paramètres → Système : affichage limité au titre et au nombre de parts
  const { hideHoldingValues } = useUI()

  const filteredHoldings = useMemo(() => {
    return holdings.filter((h) => {
      // Text search
      if (search.trim().length >= 1) {
        const q = search.toLowerCase()
        if (
          !h.asset_name?.toLowerCase().includes(q) &&
          !h.ticker?.toLowerCase().includes(q) &&
          !h.isin?.toLowerCase().includes(q)
        ) return false
      }
      // Type filter
      if (typeFilter === "etf" && !h.is_etf && !h.etf_profile_id) return false
      if (typeFilter === "action" && (h.is_etf || h.etf_profile_id)) return false
      // Perf filter
      if (!hideHoldingValues && perfFilter === "gain" && (h.gain_eur === undefined || h.gain_eur === null || h.gain_eur < 0)) return false
      if (!hideHoldingValues && perfFilter === "loss" && (h.gain_eur === undefined || h.gain_eur === null || h.gain_eur >= 0)) return false
      return true
    })
  }, [holdings, search, typeFilter, perfFilter, hideHoldingValues])

  const hasActiveFilters = search.trim().length > 0 || typeFilter !== "all" || (!hideHoldingValues && perfFilter !== "all")

  const handleDecompose = async (h: PortfolioHolding) => {
    setDecomposingId(h.id)
    const toastId = toast.loading(`Décomposition de ${h.ticker} en ligne...`)
    try {
      const res = await api.post<any>("/etf-profiles/auto-decompose", {
        symbol: h.ticker,
        name: h.asset_name,
        isin: h.isin,
      })
      if (res && res.id) {
        await api.put(`/holdings/${h.id}`, {
          etf_profile_id: res.id,
          is_etf: true,
        })
        toast.success(`${res.name} décomposé avec succès !`, { id: toastId })
        onRefresh()
      } else {
        toast.error("Impossible de décomposer ce fonds en ligne", { id: toastId })
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur de décomposition", { id: toastId })
    } finally {
      setDecomposingId(null)
    }
  }

  const totalValue = filteredHoldings.reduce((acc, h) => acc + (h.current_value_eur || 0), 0)

  const handleDelete = async (holdingId: number, name: string) => {
    if (!(await confirm(`Supprimer la position sur ${name} ?`))) return
    try {
      await api.delete(`/holdings/${holdingId}`)
      toast.success("Position supprimée")
      onRefresh()
    } catch (err: any) {
      toast.error(err?.message || "Erreur lors de la suppression")
    }
  }

  const handleTogglePaysDividends = async (h: PortfolioHolding) => {
    try {
      await api.put(`/holdings/${h.id}`, { pays_dividends: !h.pays_dividends })
      toast.success(h.pays_dividends ? `${h.ticker} : ne distribue pas` : `${h.ticker} : titre distribuant (rappel si aucun dividende pendant 13 mois)`)
      onRefresh()
    } catch (err: any) {
      toast.error(err?.message || "Erreur lors de la mise à jour")
    }
  }

  const startEditCost = (h: PortfolioHolding) => {
    setEditingCostId(h.id)
    setCostDraft(h.buy_price_avg ? String(h.buy_price_avg) : "")
  }

  const saveCost = async (h: PortfolioHolding) => {
    const value = Number(costDraft.replace(",", "."))
    if (costDraft.trim() !== "" && !(value > 0)) {
      toast.error("Le PRU doit être un nombre positif")
      return
    }
    try {
      // Vide = PRU inconnu ; le backend modifie la ligne du Point Zéro puis recalcule les positions
      await api.put(`/holdings/${h.id}`, { buy_price_avg: costDraft.trim() === "" ? null : value })
      toast.success(`PRU de ${h.ticker} mis à jour`)
      setEditingCostId(null)
      onRefresh()
    } catch (err: any) {
      toast.error(err?.message || "Impossible de modifier le PRU")
    }
  }

  const resetFilters = () => {
    setSearch("")
    setTypeFilter("all")
    setPerfFilter("all")
  }

  return { confirm, pointZeroOpen, setPointZeroOpen, costEstimateOpen, setCostEstimateOpen, editingCostId, setEditingCostId, costDraft, setCostDraft, decomposingId, setDecomposingId, search, setSearch, typeFilter, setTypeFilter, perfFilter, setPerfFilter, hideHoldingValues, filteredHoldings, hasActiveFilters, handleDecompose, totalValue, handleDelete, handleTogglePaysDividends, startEditCost, saveCost, resetFilters }
}
