import { useState, useCallback, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api"
import { useDashboardData } from "@/components/dashboard/useDashboardData"
import { DashboardHeader } from "@/components/dashboard/DashboardHeader"
import { DashboardKPIs } from "@/components/dashboard/DashboardKPIs"
import { OverviewTab } from "@/components/dashboard/tabs/OverviewTab"
import { InsightsTab } from "@/components/dashboard/tabs/InsightsTab"
import { ProjectionsTab } from "@/components/dashboard/tabs/ProjectionsTab"
import { BudgetsTab } from "@/components/dashboard/tabs/BudgetsTab"
import { MerchantsTab } from "@/components/dashboard/tabs/MerchantsTab"
import { SubscriptionsTab } from "@/components/dashboard/tabs/SubscriptionsTab"
import { HistoryTab } from "@/components/dashboard/tabs/HistoryTab"
import { AccountVerificationBanner } from "@/components/dashboard/AccountVerificationBanner"
import { MonthReviewPopup } from "@/components/month-review/MonthReviewPopup"
import { fetchCurrentBudgetMonth, formatPeriodRange, useBudgetPeriod } from "@/lib/budgetPeriod"

export default function Dashboard() {
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [accounts, setAccounts] = useState<any[]>([])
  const period = useBudgetPeriod(year, month)

  // Mois de paie : le mois affiché au départ est celui du dernier salaire reçu, pas le mois civil.
  useEffect(() => {
    fetchCurrentBudgetMonth().then(current => {
      if (current) {
        setMonth(current.month)
        setYear(current.year)
      }
    })
  }, [])
  // Vue globale par défaut, puis le dernier choix de l'utilisateur. (Basculer d'office sur le compte
  // principal rechargeait tout le tableau de bord et empêchait de rester sur « Tous les comptes ».)
  const [selectedAccountId, setSelectedAccountIdState] = useState<string>(() => {
    try {
      return localStorage.getItem("dashboard-account") || "all"
    } catch {
      return "all"
    }
  })
  const setSelectedAccountId = useCallback((id: string) => {
    setSelectedAccountIdState(id)
    try {
      localStorage.setItem("dashboard-account", id)
    } catch {
      // stockage indisponible (navigation privée) : le choix vaut pour la session
    }
  }, [])

  const fetchAccounts = useCallback(async () => {
    try {
      const accs = await api.get<any[]>("/accounts")
      const list = Array.isArray(accs) ? accs : []
      setAccounts(list)
      // Compte mémorisé supprimé ou désactivé depuis : retour à la vue globale
      setSelectedAccountIdState(current =>
        current === "all" || list.some(a => String(a.id) === current && a.active) ? current : "all"
      )
    } catch (error) {
      console.error("Failed to load accounts", error)
    }
  }, [])

  useEffect(() => {
    fetchAccounts()
  }, [fetchAccounts])

  const {
    analytics,
    expensesByCategory,
    kpiHistory,
    topMerchants,
    subscriptions,
    salarySeries,
    patrimoineAllocation,
    burnRateSeries,
    budgetAlerts,
    insights,
    sankeyData,
    projection,
    tagTotals
  } = useDashboardData(selectedAccountId, month, year)

  const selectedAccount = accounts.find(a => String(a.id) === selectedAccountId)
  const displayCurrency = selectedAccount?.currency || "EUR"

  return (
    <div className="space-y-10 pb-10">
      <MonthReviewPopup />
      <DashboardHeader 
        accounts={accounts}
        selectedAccountId={selectedAccountId}
        setSelectedAccountId={setSelectedAccountId}
        month={month}
        setMonth={setMonth}
        year={year}
        setYear={setYear}
        periodRange={formatPeriodRange(period)}
      />

      <AccountVerificationBanner 
        accounts={accounts} 
        onAccountVerified={fetchAccounts} 
      />

      <DashboardKPIs 
        selectedAccountId={selectedAccountId}
        displayCurrency={displayCurrency}
        analytics={analytics}
        kpiHistory={kpiHistory}
      />

      {/* 5 onglets (au lieu de 8) : l'onglet Investissements doublonnait la page du même nom */}
      <Tabs defaultValue="overview" className="space-y-8">
        <div className="overflow-x-auto pb-2 [ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <TabsList className="bg-slate-50/50 border border-slate-100 p-1 rounded-xl inline-flex w-max">
            <TabsTrigger value="overview" className="rounded-lg whitespace-nowrap">Aperçu</TabsTrigger>
            <TabsTrigger value="budgets" className="rounded-lg whitespace-nowrap">Budgets</TabsTrigger>
            <TabsTrigger value="spending" className="rounded-lg whitespace-nowrap">Dépenses</TabsTrigger>
            <TabsTrigger value="analysis" className="rounded-lg whitespace-nowrap">Analyse</TabsTrigger>
            <TabsTrigger value="projections" className="rounded-lg whitespace-nowrap">Projections</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="overview">
          <OverviewTab 
            sankeyData={sankeyData}
            expensesByCategory={expensesByCategory}
            displayCurrency={displayCurrency}
            tagTotals={tagTotals}
            patrimoineAllocation={patrimoineAllocation}
          />
        </TabsContent>

        <TabsContent value="budgets">
          <BudgetsTab budgetAlerts={budgetAlerts} />
        </TabsContent>

        <TabsContent value="spending" className="space-y-8">
          <MerchantsTab topMerchants={topMerchants} displayCurrency={displayCurrency} />
          <SubscriptionsTab subscriptions={subscriptions} displayCurrency={displayCurrency} />
        </TabsContent>

        <TabsContent value="analysis" className="space-y-8">
          <InsightsTab insights={insights} />
          <HistoryTab 
            kpiHistory={kpiHistory}
            burnRateSeries={burnRateSeries}
            salarySeries={salarySeries}
            displayCurrency={displayCurrency}
          />
        </TabsContent>

        <TabsContent value="projections">
          <ProjectionsTab projection={projection} displayCurrency={displayCurrency} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
