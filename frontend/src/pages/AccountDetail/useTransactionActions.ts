import { api } from "@/lib/api"
import { nowLocalInput, toInputValue, toNaiveLocal } from "@/lib/dates"
import { parsePositiveAmount } from "@/lib/utils"
import { toast } from "sonner"
import { useEffect } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"
import { useSubmit } from "@/hooks/useSubmit"
import { Transaction } from "./types"
import type { useAccountDetailState } from "./useAccountDetailState"
import type { useAccountForms } from "./useAccountForms"
import type { useAccountDetailData } from "./useAccountDetailData"

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
      toast.error("Veuillez saisir un commerçant ou un libellé")
      return
    }
    // Un Solde Initial peut valoir 0 ; toute autre opération doit avoir un montant strictement positif
    if (parsePositiveAmount(txAmount) === null && !(txType === "Solde Initial" && Number(txAmount) === 0 && txAmount !== "")) {
      toast.error("Le montant doit être un nombre supérieur à 0")
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
      await api.post("/transactions", payload)
      toast.success("Transaction ajoutée")
      setTxOpen(false)
      resetTxForm()
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error.message || "Erreur lors de l'ajout")
    }
  })

  const [handleUpdateTransaction, handleUpdateTransactionBusy] = useSubmit(async () => {
    if (!editTxId) return
    
    let merchant = txMerchant
    if (txType === "Solde Initial" && !merchant) {
      merchant = "Solde Initial"
    }

    if (!merchant) {
      toast.error("Veuillez saisir un commerçant ou un libellé")
      return
    }
    // Un Solde Initial peut valoir 0 ; toute autre opération doit avoir un montant strictement positif
    if (parsePositiveAmount(txAmount) === null && !(txType === "Solde Initial" && Number(txAmount) === 0 && txAmount !== "")) {
      toast.error("Le montant doit être un nombre supérieur à 0")
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
      await api.patch(`/transactions/${editTxId}`, payload)
      toast.success("Transaction modifiée")
      setTxOpen(false)
      resetTxForm()
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error.message || "Erreur lors de la modification")
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
    const detail = target ? ` « ${target.merchant} » de ${formatCurrency(target.amount)} (${toInputValue(target.date).slice(0, 10).split("-").reverse().join("/")})` : ""
    if (!(await confirm(`Supprimer la transaction${detail} ?`))) return
    try {
      await api.delete(`/transactions/${txId}`)
      toast.success("Transaction supprimée")
      await loadData({ quiet: true })
    } catch (error: any) {
      toast.error(error?.message || "Erreur lors de la suppression")
    }
  }

  // -- Handlers (Investment Flux) --
  return { resetTxForm, handleCreateTransaction, handleCreateTransactionBusy, handleUpdateTransaction, handleUpdateTransactionBusy, handleEditTransaction, location, navigate, searchParams, handleDeleteTransaction }
}
