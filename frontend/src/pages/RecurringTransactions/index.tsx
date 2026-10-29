import { CalendarDays, CreditCard, Repeat, Wallet } from "lucide-react"
import { IncomeTab } from "@/components/recurring/IncomeTab"
import { InvestmentFlowDialog } from "@/components/recurring/InvestmentFlowDialog"
import { PageLoader } from "@/components/layout/PageLoader"
import { Suspense, lazy } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useRecurringTransactions } from "./useRecurringTransactions"
import { RecurringHeader } from "./RecurringHeader"
import { RecurringListTab } from "./RecurringListTab"
import { SubscriptionsTab } from "./SubscriptionsTab"
import { RecurringFormDialog } from "./RecurringFormDialog"

const FinancialCalendar = lazy(() => import("@/pages/Calendar"))

export default function RecurringTransactions() {
  const ctx = useRecurringTransactions()
  const { accounts, activeTab, flowSub, recurringTxs, recurringView, setActiveTab, setFlowSub } = ctx
  return (
    <div className="space-y-6">
      <RecurringHeader ctx={ctx} />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <div className="scroll-fade-x -mx-4 overflow-x-auto px-4 md:mx-0 md:overflow-visible md:px-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <TabsList className="bg-slate-100 p-1 w-max min-w-full md:w-auto md:min-w-0 h-11 md:h-auto">
          {recurringView === "list" ? (
            <TabsTrigger value="recurring" className="rounded-lg gap-2">
              <Repeat className="h-4 w-4" />
              <span className="md:hidden">Récurrences</span><span className="hidden md:inline">Liste des Récurrences</span>
            </TabsTrigger>
          ) : (
            <TabsTrigger value="subscriptions" className="rounded-lg gap-2">
              <CreditCard className="h-4 w-4" />
              <span className="md:hidden">Récurrences</span><span className="hidden md:inline">Analyse Récurrences</span>
            </TabsTrigger>
          )}
          <TabsTrigger value="calendar" className="rounded-lg gap-2">
            <CalendarDays className="h-4 w-4" />
            Calendrier
          </TabsTrigger>
          <TabsTrigger value="salary" className="rounded-lg gap-2">
            <Wallet className="h-4 w-4" />
            <span className="md:hidden">Salaire</span><span className="hidden md:inline">Salaire & Aides</span>
          </TabsTrigger>
        </TabsList>
        </div>

        <RecurringListTab ctx={ctx} />

        <SubscriptionsTab ctx={ctx} />
        <TabsContent value="calendar" className="space-y-6">
          {/* Ex-page /calendar : chargée seulement quand l'onglet est ouvert */}
          <Suspense fallback={<PageLoader />}>
            <FinancialCalendar embedded />
          </Suspense>
        </TabsContent>

        <TabsContent value="salary" className="space-y-6">
          <IncomeTab />
        </TabsContent>
      </Tabs>

      {/* Form Dialog */}
      <InvestmentFlowDialog
        recurring={flowSub ? (recurringTxs.find((r) => r.name === flowSub.name && Math.abs(r.amount - flowSub.amount) < 0.005) ?? recurringTxs.find((r) => r.name === flowSub.name) ?? null) : null}
        accounts={accounts}
        nextOccurrence={flowSub?.next_occurrence}
        onClose={() => setFlowSub(null)}
      />
      <RecurringFormDialog ctx={ctx} />
    </div>
  )
}
