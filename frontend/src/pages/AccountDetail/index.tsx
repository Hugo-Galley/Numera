import { LoanView } from "@/components/loans/LoanView"
import { useAccountDetail } from "./useAccountDetail"
import { AccountHeader } from "./AccountHeader"
import { FilterBar } from "./FilterBar"
import { AccountKpis } from "./AccountKpis"
import { AccountCharts } from "./AccountCharts"
import { TransactionsSection } from "./TransactionsSection"
import { InvestmentSection } from "./InvestmentSection"
import { BulkActionsBar } from "./BulkActionsBar"
import { BulkEditDialog } from "./BulkEditDialog"
import { AccountDialogs } from "./AccountDialogs"

export default function AccountDetail() {
  const ctx = useAccountDetail()
  const { loading, account, investmentData } = ctx

  if (loading) return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        <p className="text-slate-500 font-medium">Chargement du compte...</p>
      </div>
    </div>
  )
  
  if (!account) return <div>Compte non trouvé</div>
  // Un compte crédit n'a pas d'opérations : échéancier, capital restant dû et simulateur
  if (account.type === "credit") return <LoanView accountId={account.id} />

  const isInvestment = account.type === "investissement" || account.type === "assurance_vie"
  const currentBalance = isInvestment 
    ? (investmentData?.totals?.current_value || 0)
    : (account.balance ?? 0)  // calculé par le backend : transactions[0] dépend des filtres/tri actifs
  const view = { ...ctx, account, isInvestment, currentBalance }

  return (
    <div className="space-y-8 pb-10">
      {/* Breadcrumbs & Header */}
      <div className="flex flex-col gap-6">
        <AccountHeader ctx={view} />

        <FilterBar ctx={view} />
      </div>

      <AccountKpis ctx={view} />

      <AccountCharts ctx={view} />

      <TransactionsSection ctx={view} />

      <InvestmentSection ctx={view} />
      <BulkActionsBar ctx={view} />

      <BulkEditDialog ctx={view} />

      <AccountDialogs ctx={view} />
    </div>
  )
}
