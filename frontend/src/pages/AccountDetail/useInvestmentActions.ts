import { PortfolioHolding } from "@/types/diversity"
import { api } from "@/lib/api"
import { errorMessage } from "@/lib/utils"
import { nowLocalInput, toInputValue, toNaiveLocal, todayLocal } from "@/lib/dates"
import { toast } from "sonner"
import { useSubmit } from "@/hooks/useSubmit"
import type { useAccountDetailState } from "./useAccountDetailState"
import type { useAccountForms } from "./useAccountForms"
import type { useAccountDetailData } from "./useAccountDetailData"
import type { useTransactionActions } from "./useTransactionActions"

/** Flux d'investissement, snapshots, modification groupée et point zéro. */
export function useInvestmentActions(p: ReturnType<typeof useAccountDetailState> & ReturnType<typeof useAccountForms> & ReturnType<typeof useAccountDetailData> & ReturnType<typeof useTransactionActions>) {
  const { confirm, id, account, transactions, selectedIds, setSelectedIds, setIsBulkEditDialogOpen, bulkCategory, bulkRecurring, bulkTagIds, bulkTagAction, setSnapOpen, editSnapId, setEditSnapId, snapDate, setSnapDate, snapValue, setSnapValue, snapNote, setSnapNote, setInvTxOpen, editInvTxId, setEditInvTxId, invTxDate, setInvTxDate, invTxType, setInvTxType, invTxAmount, setInvTxAmount, invTxCurrency, setInvTxCurrency, invTxNote, setInvTxNote, invTxTicker, setInvTxTicker, invTxIsin, setInvTxIsin, invTxQuantity, setInvTxQuantity, invTxUnitPrice, setInvTxUnitPrice, invTxFees, setInvTxFees, invTxWithholding, setInvTxWithholding, invTxReinvested, setInvTxReinvested, invTxAssetClass, setInvTxAssetClass, invTxSector, setInvTxSector, invTxZone, setInvTxZone, setZeroOpen, zeroDate, setZeroDate, zeroValue, setZeroValue, zeroNote, setZeroNote, loadData } = p
  const resetInvTxForm = () => {
    setEditInvTxId(null)
    setInvTxDate(nowLocalInput())
    setInvTxType("versement")
    setInvTxAmount("")
    setInvTxCurrency(account?.currency || "EUR")
    setInvTxNote("")
    setInvTxTicker("")
    setInvTxIsin("")
    setInvTxQuantity("")
    setInvTxUnitPrice("")
    setInvTxFees("")
    setInvTxWithholding("")
    setInvTxReinvested(false)
    setInvTxAssetClass("")
    setInvTxSector("")
    setInvTxZone("")
  }

  const [handleCreateInvestmentTransaction, handleCreateInvestmentTransactionBusy] = useSubmit(async () => {
    if (!invTxAmount && (!invTxQuantity || !invTxUnitPrice)) {
      toast.error("Veuillez saisir un montant ou un nombre de parts")
      return
    }
    if (invTxType === "dividende" && !invTxTicker) {
      toast.error("Un dividende doit être rattaché à un titre")
      return
    }
    if (invTxType === "dividende" && invTxReinvested && !invTxQuantity) {
      toast.error("Indique le nombre de parts reçues pour un dividende réinvesti")
      return
    }
    try {
      const calculatedAmount = invTxAmount 
        ? Number(invTxAmount) 
        : (Number(invTxQuantity || 0) * Number(invTxUnitPrice || 0))

      const payload = {
        account_id: Number(id),
        date: toNaiveLocal(invTxDate),
        type: invTxType,
        amount: calculatedAmount,
        currency: invTxCurrency,
        note: invTxNote || null,
        ticker: invTxTicker ? invTxTicker.trim().toUpperCase() : null,
        isin: invTxIsin ? invTxIsin.trim().toUpperCase() : null,
        quantity: invTxQuantity ? Number(invTxQuantity) : null,
        unit_price: invTxUnitPrice ? Number(invTxUnitPrice) : null,
        // Le prix unitaire et les frais sont saisis dans la devise de l'opération
        price_currency: invTxUnitPrice ? invTxCurrency : null,
        fees: invTxFees ? Number(invTxFees) : null,
        withholding_tax: invTxType === "dividende" && invTxWithholding ? Number(invTxWithholding) : null,
        reinvested: invTxType === "dividende" && invTxReinvested,
        asset_class: invTxAssetClass || null,
        sector: invTxSector || null,
        geographic_zone: invTxZone || null
      }
      
      if (editInvTxId) {
        await api.patch(`/investment-transactions/${editInvTxId}`, payload)
        toast.success("Opération modifiée")
      } else {
        await api.post("/investment-transactions", payload)
        toast.success("Opération enregistrée")
      }
      
      setInvTxOpen(false)
      resetInvTxForm()
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error.message || "Erreur lors de l'enregistrement")
    }
  })

  const handleEditInvTransaction = (tx: any) => {
    setEditInvTxId(tx.id)
    setInvTxDate(toInputValue(tx.date))
    setInvTxType(tx.type)
    setInvTxAmount(String(tx.original_amount || tx.amount))
    setInvTxCurrency(tx.currency || account?.currency || "EUR")
    setInvTxNote(tx.note || "")
    setInvTxTicker(tx.ticker || "")
    setInvTxIsin(tx.isin || "")
    setInvTxQuantity(tx.quantity != null ? String(tx.quantity) : "")
    setInvTxUnitPrice(tx.unit_price != null ? String(tx.unit_price) : "")
    setInvTxFees(tx.fees != null ? String(tx.fees) : "")
    setInvTxWithholding(tx.withholding_tax != null ? String(tx.withholding_tax) : "")
    setInvTxReinvested(Boolean(tx.reinvested))
    setInvTxAssetClass(tx.asset_class || "")
    setInvTxSector(tx.sector || "")
    setInvTxZone(tx.geographic_zone || "")
    setInvTxOpen(true)
  }

  // Bouton « Dividende » d'une position : ouvre le formulaire de flux prérempli avec le titre
  const handleAddDividend = (holding: PortfolioHolding) => {
    resetInvTxForm()
    setInvTxType("dividende")
    setInvTxTicker(holding.ticker)
    setInvTxIsin(holding.isin || "")
    setInvTxNote(`Dividende ${holding.asset_name}`)
    setInvTxOpen(true)
  }

  const handleDeleteInvTransaction = async (txId: number) => {
    if (!(await confirm("Supprimer ce flux ?"))) return
    try {
      await api.delete(`/investment-transactions/${txId}`)
      toast.success("Flux supprimé")
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error?.message || "Erreur lors de la suppression")
    }
  }

  // -- Handlers (Snapshots) --
  const resetSnapForm = () => {
    setEditSnapId(null)
    setSnapDate(todayLocal())
    setSnapValue("")
    setSnapNote("")
  }

  const [handleCreateSnapshot, handleCreateSnapshotBusy] = useSubmit(async () => {
    if (snapValue === "" || !Number.isFinite(Number(String(snapValue).replace(",", "."))) || Number(String(snapValue).replace(",", ".")) < 0) {
      toast.error("Saisissez une valeur valide (nombre positif ou nul)")
      return
    }
    try {
      const payload = {
        account_id: Number(id),
        date: snapDate,
        current_value: Number(snapValue),
        note: snapNote || null,
        is_zero_point: false
      }

      if (editSnapId) {
        await api.patch(`/balance-snapshots/${editSnapId}`, payload)
        toast.success("Snapshot modifié")
      } else {
        await api.post("/balance-snapshots", payload)
        toast.success("Snapshot enregistré")
      }
      
      setSnapOpen(false)
      resetSnapForm()
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de l'enregistrement"))
    }
  })

  const handleEditSnapshot = (snap: any) => {
    setEditSnapId(snap.id)
    setSnapDate(snap.date.slice(0, 10))
    setSnapValue(String(snap.current_value))
    setSnapNote(snap.note || "")
    setSnapOpen(true)
  }

  const handleDeleteSnapshot = async (snapId: number) => {
    if (!(await confirm("Supprimer ce snapshot ?"))) return
    try {
      await api.delete(`/balance-snapshots/${snapId}`)
      toast.success("Snapshot supprimé")
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de la suppression"))
    }
  }

  const [handleBulkUpdate] = useSubmit(async () => {
    try {
      const payload: any = { ids: selectedIds }
      if (bulkCategory !== "keep") {
        payload.category_id = bulkCategory === "none" ? null : Number(bulkCategory)
      }
      if (bulkRecurring !== "keep") {
        payload.is_recurring = bulkRecurring === "true"
      }
      if (bulkTagAction === "replace") {
        payload.tag_ids = bulkTagIds
      }

      await api.patch("/transactions/bulk", payload)
      toast.success(`${selectedIds.length} transactions mises à jour`)
      setSelectedIds([])
      setIsBulkEditDialogOpen(false)
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de la mise à jour groupée"))
    }
  })

  // -- Handlers (Zero Point) --
  const resetZeroForm = () => {
    setZeroDate(todayLocal())
    setZeroValue("")
    setZeroNote("")
  }

  const [handleSetZeroPoint, handleSetZeroPointBusy] = useSubmit(async () => {
    if (zeroValue === "" || !Number.isFinite(Number(String(zeroValue).replace(",", "."))) || Number(String(zeroValue).replace(",", ".")) < 0) {
      toast.error("Saisissez une valeur d'ouverture valide (nombre positif ou nul)")
      return
    }
    try {
      const payload = {
        account_id: Number(id),
        date: toNaiveLocal(zeroDate),
        current_value: Number(zeroValue),
        note: zeroNote || null
      }
      await api.post("/balance-snapshots/set-zero-point", payload)
      toast.success("Nouveau point zéro défini")
      setZeroOpen(false)
      resetZeroForm()
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de la définition du point zéro"))
    }
  })

  // -- Memos --
  return { resetInvTxForm, handleCreateInvestmentTransaction, handleCreateInvestmentTransactionBusy, handleEditInvTransaction, handleAddDividend, handleDeleteInvTransaction, resetSnapForm, handleCreateSnapshot, handleCreateSnapshotBusy, handleEditSnapshot, handleDeleteSnapshot, handleBulkUpdate, resetZeroForm, handleSetZeroPoint, handleSetZeroPointBusy }
}
