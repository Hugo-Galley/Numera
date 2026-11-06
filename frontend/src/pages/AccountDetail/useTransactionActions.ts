import { nowLocalInput, toInputValue, toNaiveLocal } from "@/lib/dates"
import { parsePositiveAmount } from "@/lib/utils"
import i18n from "i18next"
import { toast } from "sonner"
import { useEffect } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"
import { useSubmit } from "@/hooks/useSubmit"
import { Transaction } from "./types"
import type { useAccountDetailState } from "./useAccountDetailState"
import type { useAccountForms } from "./useAccountForms"
import type { useAccountDetailData } from "./useAccountDetailData"
import { deleteTransactionsById, patchTransactionsById, postTransactions } from "@/lib/api/transactions"

/** Création, modification et suppression des transactions du compte. */
export function useTransactionActions(p: ReturnType<typeof useAccountDetailState> & ReturnType<typeof useAccountForms> & ReturnType<typeof useAccountDetailData>) {
  const { confirm, id, account, transactions, formatCurrency, setTxOpen, editTxId, setEditTxId, txDate, setTxDate, txType, setTxType, txMerchant, setTxMerchant, txAmount, setTxAmount, txCurrency, setTxCurrency, txCategoryId, setTxCategoryId, txTagIds, setTxTagIds, txNote, setTxNote, txIsRecurring, setTxIsRecurring, txIsExceptional, setTxIsExceptional, txCustomIcon, setTxCustomIcon, txCustomColor, setTxCustomColor, loadData } = p
  const resetTxForm = () => {
    setEditTxId(null)
    setTxDate(nowLocalInput())
    setTxType("Sortie")
    setTxMerchant("")
    setTxAmount("")
    setTxCurrency(account?.currency || "EUR")
    setTxCategoryId("none")
    setTxTagIds([])
    setTxNote("")
    setTxIsRecurring(false)
    setTxIsExceptional(false)
    setTxCustomIcon("")
    setTxCustomColor("#0f172a")
  }

  const [handleCreateTransaction, handleCreateTransactionBusy] = useSubmit(async () => {
    let merchant = txMerchant
    if (txType === "Solde Initial" && !merchant) {
      merchant = "Solde Initial"
    }

    if (!merchant) {
      toast.error(i18n.t("tx.toast.needMerchant", { ns: "accountDetail" }))
      return
    }
    // Un Solde Initial peut valoir 0 ; toute autre opération doit avoir un montant strictement positif
    if (parsePositiveAmount(txAmount) === null && !(txType === "Solde Initial" && Number(txAmount) === 0 && txAmount !== "")) {
      toast.error(i18n.t("tx.toast.needAmount", { ns: "accountDetail" }))
      return
    }

    try {
      const payload = {
        account_id: Number(id),
        date: toNaiveLocal(txDate),
        type: txType,
        merchant: merchant,
        category_id: txCategoryId && txCategoryId !== "none" ? Number(txCategoryId) : null,
        tag_ids: txTagIds,
        amount: Number(txAmount),
        currency: txCurrency,
        note: txNote || null,
        is_recurring: txIsRecurring,
        is_exceptional: txType === "Sortie" && txIsExceptional,
        custom_icon: txCustomIcon || null,
        custom_color: txCustomColor || null
      }
      await postTransactions(payload)
      toast.success(i18n.t("tx.toast.added", { ns: "accountDetail" }))
      setTxOpen(false)
      resetTxForm()
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error.message || i18n.t("tx.toast.addError", { ns: "accountDetail" }))
    }
  })

  const [handleUpdateTransaction, handleUpdateTransactionBusy] = useSubmit(async () => {
    if (!editTxId) return
    
    let merchant = txMerchant
    if (txType === "Solde Initial" && !merchant) {
      merchant = "Solde Initial"
    }

    if (!merchant) {
      toast.error(i18n.t("tx.toast.needMerchant", { ns: "accountDetail" }))
      return
    }
    // Un Solde Initial peut valoir 0 ; toute autre opération doit avoir un montant strictement positif
    if (parsePositiveAmount(txAmount) === null && !(txType === "Solde Initial" && Number(txAmount) === 0 && txAmount !== "")) {
      toast.error(i18n.t("tx.toast.needAmount", { ns: "accountDetail" }))
      return
    }

    try {
      const payload: any = {
        date: toNaiveLocal(txDate),
        type: txType,
        merchant: merchant,
        category_id: txCategoryId && txCategoryId !== "none" ? Number(txCategoryId) : null,
        tag_ids: txTagIds,
        amount: Number(txAmount),
        currency: txCurrency,
        note: txNote || null,
        is_recurring: txIsRecurring,
        is_exceptional: txType === "Sortie" && txIsExceptional,
        custom_icon: txCustomIcon || null,
        custom_color: txCustomColor || null
      }
      await patchTransactionsById(editTxId, payload)
      toast.success(i18n.t("tx.toast.updated", { ns: "accountDetail" }))
      setTxOpen(false)
      resetTxForm()
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error.message || i18n.t("tx.toast.updateError", { ns: "accountDetail" }))
    }
  })

  const handleEditTransaction = (tx: Transaction) => {
    setEditTxId(tx.id)
    setTxDate(toInputValue(tx.date))
    setTxType(tx.type)
    setTxMerchant(tx.merchant)
    setTxAmount(String(tx.original_amount || tx.amount))
    setTxCurrency(tx.currency || account?.currency || "EUR")
    setTxCategoryId(tx.category_id ? String(tx.category_id) : "none")
    setTxTagIds(tx.tags?.map(t => t.id) || [])
    setTxNote(tx.note || "")
    setTxIsRecurring(tx.is_recurring)
    setTxIsExceptional(!!tx.is_exceptional)
    setTxCustomIcon(tx.custom_icon || "")
    setTxCustomColor(tx.custom_color || "#0f172a")
    setTxOpen(true)
  }

  // Ouverture depuis ⌘K : saisie rapide (?new=tx&type=&amount=&merchant=) ou transaction trouvée (state)
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  useEffect(() => {
    if (!account) return
    const openTransaction = (location.state as { openTransaction?: Transaction } | null)?.openTransaction
    if (openTransaction && openTransaction.account_id === account.id) {
      handleEditTransaction(openTransaction)
    } else if (searchParams.get("new") === "tx") {
      resetTxForm()
      const type = searchParams.get("type")
      if (type === "Sortie" || type === "Entree") setTxType(type)
      setTxAmount(searchParams.get("amount") ?? "")
      setTxMerchant(searchParams.get("merchant") ?? "")
      setTxCurrency(account.currency || "EUR")
      setTxOpen(true)
    } else {
      return
    }
    navigate(location.pathname, { replace: true, state: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [account?.id, location.key])

  const handleDeleteTransaction = async (txId: number) => {
    const target = transactions.find((t) => t.id === txId)
    const detail = target ? i18n.t("tx.toast.deleteDetail", { ns: "accountDetail", merchant: target.merchant, amount: formatCurrency(target.amount), date: toInputValue(target.date).slice(0, 10).split("-").reverse().join("/") }) : ""
    if (!(await confirm(i18n.t("tx.toast.confirmDelete", { ns: "accountDetail", detail })))) return
    try {
      await deleteTransactionsById(txId)
      toast.success(i18n.t("tx.toast.deleted", { ns: "accountDetail" }))
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error?.message || i18n.t("tx.toast.deleteError", { ns: "accountDetail" }))
    }
  }

  // -- Handlers (Investment Flux) --
  return { resetTxForm, handleCreateTransaction, handleCreateTransactionBusy, handleUpdateTransaction, handleUpdateTransactionBusy, handleEditTransaction, location, navigate, searchParams, handleDeleteTransaction }
}
