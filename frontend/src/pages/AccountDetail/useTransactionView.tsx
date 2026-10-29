import { ArrowRightLeft, HandCoins, MoreHorizontal, Pencil, Split, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { WorkHours } from "@/components/ui/work-hours"
import { endOfDayParam, startOfDayParam } from "@/lib/dates"
import { useEffect, useMemo } from "react"
import { Transaction } from "./types"
import type { useAccountDetailState } from "./useAccountDetailState"
import type { useAccountForms } from "./useAccountForms"
import type { useAccountDetailData } from "./useAccountDetailData"
import type { useTransactionActions } from "./useTransactionActions"
import type { useInvestmentActions } from "./useInvestmentActions"
import { getAnalyticsAccountFlowSummary } from "@/lib/api/analytics"

/** Vue de la liste : filtres locaux, tri, statistiques et menu d'actions d'une ligne. */
export function useTransactionView(p: ReturnType<typeof useAccountDetailState> & ReturnType<typeof useAccountForms> & ReturnType<typeof useAccountDetailData> & ReturnType<typeof useTransactionActions> & ReturnType<typeof useInvestmentActions>) {
  const { id, account, setReimbursementTx, setSplitTx, transactions, flowSummary, setFlowSummary, debouncedSearch, dateStart, dateEnd, sortField, sortOrder, txDate, openTransferDialog, handleEditTransaction, handleDeleteTransaction } = p
  const filteredTransactions = useMemo(() => {
    return transactions
      .filter(tx => {
        const txDate = new Date(tx.date)

        let matchesDate = true
        if (dateStart) {
          const start = new Date(dateStart)
          start.setHours(0, 0, 0, 0)
          matchesDate = matchesDate && txDate >= start
        }
        if (dateEnd) {
          const end = new Date(dateEnd)
          end.setHours(23, 59, 59, 999)
          matchesDate = matchesDate && txDate <= end
        }

        return matchesDate
      })
      .sort((a, b) => {
        let comparison = 0
        switch (sortField) {
          case "date":
            comparison = new Date(a.date).getTime() - new Date(b.date).getTime()
            break
          case "merchant":
            comparison = a.merchant.localeCompare(b.merchant)
            break
          case "amount":
            comparison = a.amount - b.amount
            break
          case "category":
            const getDisplayCategory = (tx: Transaction) => {
              if (tx.type === "Solde Initial") return "Solde Initial"
              if (tx.type === "Interets") return "Intérêts"
              return tx.category?.name || "Sans catégorie"
            }
            comparison = getDisplayCategory(a).localeCompare(getDisplayCategory(b))
            break
          case "type":
            comparison = a.type.localeCompare(b.type)
            break
          case "running_balance":
            comparison = a.running_balance - b.running_balance
            break
        }
        
        // Secondary sort by ID for stability
        if (comparison === 0) {
          comparison = a.id - b.id
        }
        
        return sortOrder === "asc" ? comparison : -comparison
      })
  }, [transactions, dateStart, dateEnd, sortField, sortOrder])

  // KPI calculés par le backend (tout l'historique du compte, virements exclus) :
  // la liste chargée ici est paginée et ne suffit pas à les calculer correctement.
  useEffect(() => {
    if (!id) return
    const params = new URLSearchParams({ account_id: id })
    if (dateStart) params.append("start_date", startOfDayParam(dateStart))
    if (dateEnd) params.append("end_date", endOfDayParam(dateEnd))
    getAnalyticsAccountFlowSummary<typeof flowSummary>(`?${params.toString()}`)
      .then(setFlowSummary)
      .catch(() => setFlowSummary(null))
  }, [id, dateStart, dateEnd, transactions])

  const stats = useMemo(() => {
    const source = (debouncedSearch || dateStart || dateEnd) ? filteredTransactions : transactions
    if (source.length === 0 || !flowSummary) return null
    // Recherche texte : la moyenne porte sur les lignes affichées (le backend ne filtre pas par texte)
    const searchedExpenses = debouncedSearch ? source.filter(t => t.type === "Sortie") : []
    return {
      monthlyNetFlow: flowSummary.monthly_net_flow,
      monthlyVariation: flowSummary.monthly_variation,
      prevMonthlyNetFlow: flowSummary.prev_monthly_net_flow,
      count: source.length,
      avgTx: debouncedSearch
        ? (searchedExpenses.length > 0 ? searchedExpenses.reduce((acc, t) => acc + t.amount, 0) / searchedExpenses.length : 0)
        : flowSummary.avg_expense,
    }
  }, [transactions, filteredTransactions, flowSummary, debouncedSearch, dateStart, dateEnd])

  const renderTxMenu = (tx: any) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="h-10 w-10 p-0 md:h-8 md:w-8" title="Actions">
            <MoreHorizontal className="h-4 w-4 text-slate-500" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" collisionPadding={12} className="w-56 max-md:[&_[role=menuitem]]:min-h-11">
          {tx.type === "Sortie" && !tx.is_transfer && account?.currency === "EUR" && (
            <>
              <DropdownMenuLabel className="py-1">
                <WorkHours amount={tx.amount - (tx.reimbursement_offset ?? 0)} className="text-xs text-slate-500" />
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
            </>
          )}
          {(tx.type === "Sortie" || tx.type === "Entree") && !tx.is_transfer && (
            <DropdownMenuItem onClick={() => setReimbursementTx(tx)}>
              <HandCoins className="mr-2 h-4 w-4" />
              {tx.type === "Sortie" ? "On me doit…" : "Affecter à une créance…"}
            </DropdownMenuItem>
          )}
          {tx.type === "Sortie" && !tx.is_transfer && (
            <DropdownMenuItem onClick={() => setSplitTx(tx)}>
              <Split className="mr-2 h-4 w-4" />
              {tx.splits?.length ? "Modifier le découpage…" : "Découper entre catégories…"}
            </DropdownMenuItem>
          )}
          {(tx.type === "Sortie" || tx.type === "Entree") && (
            <DropdownMenuItem onClick={() => openTransferDialog(tx)}>
              <ArrowRightLeft className="mr-2 h-4 w-4" />
              {tx.is_transfer ? "Virement interne lié…" : "Virement interne…"}
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onClick={() => handleEditTransaction(tx)}>
            <Pencil className="mr-2 h-4 w-4" />
            Modifier
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => handleDeleteTransaction(tx.id)} className="text-rose-600 focus:text-rose-600">
            <Trash2 className="mr-2 h-4 w-4" />
            Supprimer
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
  )

  return { filteredTransactions, stats, renderTxMenu }
}
