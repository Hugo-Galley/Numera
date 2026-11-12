import i18n from "i18next"
import { PortfolioHolding } from "@/types/diversity"
import { errorMessage } from "@/lib/utils"
import { nowLocalInput, toInputValue, toNaiveLocal, todayLocal } from "@/lib/dates"
import { toast } from "sonner"
import { useSubmit } from "@/hooks/useSubmit"
import type { useAccountDetailState } from "./useAccountDetailState"
import type { useAccountForms } from "./useAccountForms"
import type { useAccountDetailData } from "./useAccountDetailData"
import type { useTransactionActions } from "./useTransactionActions"
import { deleteBalanceSnapshotsById, patchBalanceSnapshotsById, postBalanceSnapshots, postBalanceSnapshotsSetZeroPoint } from "@/lib/api/accounts"
import { deleteInvestmentTransactionsById, patchInvestmentTransactionsById, postInvestmentTransactions } from "@/lib/api/investments"
import { patchTransactionsBulk } from "@/lib/api/transactions"
import type { ApiBody } from "@/lib/api/types"
import type { InvestmentFlow, ValueSnapshot } from "./types"

/** Flux d'investissement, snapshots, modification groupée et point zéro. */
export function useInvestmentActions(p: ReturnType<typeof useAccountDetailState> & ReturnType<typeof useAccountForms> & ReturnType<typeof useAccountDetailData> & ReturnType<typeof useTransactionActions>) {
  const { confirm, id, account, selectedIds, setSelectedIds, setIsBulkEditDialogOpen, bulkCategory, bulkRecurring, bulkTagIds, bulkTagAction, setSnapOpen, editSnapId, setEditSnapId, snapDate, setSnapDate, snapValue, setSnapValue, snapNote, setSnapNote, setInvTxOpen, editInvTxId, setEditInvTxId, invTxDate, setInvTxDate, invTxType, setInvTxType, invTxAmount, setInvTxAmount, invTxCurrency, setInvTxCurrency, invTxNote, setInvTxNote, invTxTicker, setInvTxTicker, invTxIsin, setInvTxIsin, invTxQuantity, setInvTxQuantity, invTxUnitPrice, setInvTxUnitPrice, invTxFees, setInvTxFees, invTxWithholding, setInvTxWithholding, invTxReinvested, setInvTxReinvested, invTxAssetClass, setInvTxAssetClass, invTxSector, setInvTxSector, invTxZone, setInvTxZone, setZeroOpen, zeroDate, setZeroDate, zeroValue, setZeroValue, zeroNote, setZeroNote, loadData } = p
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
      toast.error(i18n.t("useInvestmentActions.veuillezSaisirUnMontantOu", { ns: "accountDetail" }))
      return
    }
    if (invTxType === "dividende" && !invTxTicker) {
      toast.error(i18n.t("useInvestmentActions.unDividendeDoitEtreRattache", { ns: "accountDetail" }))
      return
    }
    if (invTxType === "dividende" && invTxReinvested && !invTxQuantity) {
      toast.error(i18n.t("useInvestmentActions.indiqueLeNombreDeParts", { ns: "accountDetail" }))
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
        await patchInvestmentTransactionsById(editInvTxId, payload)
        toast.success(i18n.t("useInvestmentActions.operationModifiee", { ns: "accountDetail" }))
      } else {
        await postInvestmentTransactions(payload)
        toast.success(i18n.t("useInvestmentActions.operationEnregistree", { ns: "accountDetail" }))
      }
      
      setInvTxOpen(false)
      resetInvTxForm()
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, i18n.t("useInvestmentActions.erreurLorsDeLEnregistrement", { ns: "accountDetail" })))
    }
  })

  const handleEditInvTransaction = (tx: InvestmentFlow) => {
    setEditInvTxId(tx.id)
    setInvTxDate(toInputValue(tx.date))
    // Le contrat décrit `type` comme une chaîne ; les valeurs possibles sont celles du sélecteur
    setInvTxType(tx.type as Parameters<typeof setInvTxType>[0])
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
    if (!(await confirm(i18n.t("useInvestmentActions.supprimerCeFlux", { ns: "accountDetail" })))) return
    try {
      await deleteInvestmentTransactionsById(txId)
      toast.success(i18n.t("useInvestmentActions.fluxSupprime", { ns: "accountDetail" }))
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, i18n.t("useInvestmentActions.erreurLorsDeLaSuppression", { ns: "accountDetail" })))
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
      toast.error(i18n.t("useInvestmentActions.saisissezUneValeurValideNombre", { ns: "accountDetail" }))
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
        await patchBalanceSnapshotsById(editSnapId, payload)
        toast.success(i18n.t("useInvestmentActions.snapshotModifie", { ns: "accountDetail" }))
      } else {
        await postBalanceSnapshots(payload)
        toast.success(i18n.t("useInvestmentActions.snapshotEnregistre", { ns: "accountDetail" }))
      }
      
      setSnapOpen(false)
      resetSnapForm()
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, i18n.t("useInvestmentActions.erreurLorsDeLEnregistrement", { ns: "accountDetail" })))
    }
  })

  const handleEditSnapshot = (snap: ValueSnapshot) => {
    setEditSnapId(snap.id)
    setSnapDate(snap.date.slice(0, 10))
    setSnapValue(String(snap.current_value))
    setSnapNote(snap.note || "")
    setSnapOpen(true)
  }

  const handleDeleteSnapshot = async (snapId: number) => {
    if (!(await confirm(i18n.t("useInvestmentActions.supprimerCeSnapshot", { ns: "accountDetail" })))) return
    try {
      await deleteBalanceSnapshotsById(snapId)
      toast.success(i18n.t("useInvestmentActions.snapshotSupprime", { ns: "accountDetail" }))
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, i18n.t("useInvestmentActions.erreurLorsDeLaSuppression", { ns: "accountDetail" })))
    }
  }

  const [handleBulkUpdate] = useSubmit(async () => {
    try {
      const payload: ApiBody<"/transactions/bulk", "patch"> = { ids: selectedIds }
      if (bulkCategory !== "keep") {
        payload.category_id = bulkCategory === "none" ? null : Number(bulkCategory)
      }
      if (bulkRecurring !== "keep") {
        payload.is_recurring = bulkRecurring === "true"
      }
      if (bulkTagAction === "replace") {
        payload.tag_ids = bulkTagIds
      }

      await patchTransactionsBulk(payload)
      toast.success(i18n.t("investmentActions.bulkUpdated", { ns: "accountDetail", count: selectedIds.length }))
      setSelectedIds([])
      setIsBulkEditDialogOpen(false)
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, i18n.t("useInvestmentActions.erreurLorsDeLaMise", { ns: "accountDetail" })))
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
      toast.error(i18n.t("useInvestmentActions.saisissezUneValeurDOuverture", { ns: "accountDetail" }))
      return
    }
    try {
      const payload = {
        account_id: Number(id),
        date: toNaiveLocal(zeroDate),
        current_value: Number(zeroValue),
        note: zeroNote || null
      }
      await postBalanceSnapshotsSetZeroPoint(payload)
      toast.success(i18n.t("useInvestmentActions.nouveauPointZeroDefini", { ns: "accountDetail" }))
      setZeroOpen(false)
      resetZeroForm()
      await loadData({ quiet: true })
    } catch (error) {
      toast.error(errorMessage(error, i18n.t("useInvestmentActions.erreurLorsDeLaDefinition", { ns: "accountDetail" })))
    }
  })

  // -- Memos --
  return { resetInvTxForm, handleCreateInvestmentTransaction, handleCreateInvestmentTransactionBusy, handleEditInvTransaction, handleAddDividend, handleDeleteInvTransaction, resetSnapForm, handleCreateSnapshot, handleCreateSnapshotBusy, handleEditSnapshot, handleDeleteSnapshot, handleBulkUpdate, resetZeroForm, handleSetZeroPoint, handleSetZeroPointBusy }
}
