import { useState, useCallback, useEffect } from "react"
import { useNavigate } from "react-router-dom"
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
import { InvestmentsTab } from "@/components/dashboard/tabs/InvestmentsTab"
import { HistoryTab } from "@/components/dashboard/tabs/HistoryTab"

export default function Dashboard() {
  const navigate = useNavigate()
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [accounts, setAccounts] = useState<any[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>("all")

  useEffect(() => {
    async function init() {
      try {
        const accs = await api.get<any[]>("/accounts")
        if (accs && Array.isArray(accs)) {
          setAccounts(accs)
          const mainAcc = accs.find(a => a.is_main && a.active)
          if (mainAcc) {
            setSelectedAccountId(String(mainAcc.id))
          } else {
            const defaultAcc = accs.find(a => a.type === "courant" && a.active)
            if (defaultAcc) {
              setSelectedAccountId(String(defaultAcc.id))
            }
          }
        } else {
          setAccounts([])
        }
      } catch (error) {
        console.error("Failed to load accounts", error)
      }
    }
    init()
  }, [])

  const {
    analytics,
    expensesByCategory,
    kpiHistory,
    topMerchants,
    subscriptions,
    salarySeries,
    investments,
    allocation,
    burnRateSeries,
    budgetAlerts,
    insights,
    sankeyData,
    projection,
    tagTotals
  } = useDashboardData(selectedAccountId, month, year)

  const onAllocationClick = useCallback((_: any, index: number) => {
    const item = allocation?.items?.[index]
    if (item && item.account_id) {
      navigate(`/accounts/${item.account_id}`)
    }
  }, [allocation, navigate])

  const onInvestmentBarClick = useCallback((data: any) => {
    if (data && data.account_id) {
      navigate(`/accounts/${data.account_id}`)
    }
  }, [navigate])

  const selectedAccount = accounts.find(a => String(a.id) === selectedAccountId)
  const displayCurrency = selectedAccount?.currency || "EUR"

  return (
    <div className="space-y-10 pb-10">
      <DashboardHeader 
        accounts={accounts}
        selectedAccountId={selectedAccountId}
        setSelectedAccountId={setSelectedAccountId}
        month={month}
        setMonth={setMonth}
        year={year}
        setYear={setYear}
      />

      <DashboardKPIs 
        selectedAccountId={selectedAccountId}
        displayCurrency={displayCurrency}
        analytics={analytics}
        kpiHistory={kpiHistory}
      />

      <Tabs defaultValue="overview" className="space-y-8">
        <div className="overflow-x-auto pb-2 [ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <TabsList className="bg-slate-50/50 border border-slate-100 p-1 rounded-xl inline-flex w-max">
            <TabsTrigger value="overview" className="rounded-lg whitespace-nowrap">Aperçu Général</TabsTrigger>
            <TabsTrigger value="insights" className="rounded-lg whitespace-nowrap">Insights</TabsTrigger>
            <TabsTrigger value="merchants" className="rounded-lg whitespace-nowrap">Top Commerçants</TabsTrigger>
            <TabsTrigger value="budgets" className="rounded-lg whitespace-nowrap">Budgets</TabsTrigger>
            <TabsTrigger value="subscriptions" className="rounded-lg whitespace-nowrap">Abonnements</TabsTrigger>
            <TabsTrigger value="investments" className="rounded-lg whitespace-nowrap">Investissements</TabsTrigger>
            <TabsTrigger value="history" className="rounded-lg whitespace-nowrap">Évolutions</TabsTrigger>
            <TabsTrigger value="projections" className="rounded-lg whitespace-nowrap">Projections</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="overview">
          <OverviewTab 
            sankeyData={sankeyData}
            expensesByCategory={expensesByCategory}
            displayCurrency={displayCurrency}
            tagTotals={tagTotals}
          />
        </TabsContent>

        <TabsContent value="insights">
          <InsightsTab insights={insights} />
        </TabsContent>

        <TabsContent value="projections">
          <ProjectionsTab projection={projection} displayCurrency={displayCurrency} />
        </TabsContent>

        <TabsContent value="budgets">
          <BudgetsTab budgetAlerts={budgetAlerts} />
        </TabsContent>

        <TabsContent value="merchants">
          <MerchantsTab topMerchants={topMerchants} displayCurrency={displayCurrency} />
        </TabsContent>

        <TabsContent value="subscriptions">
          <SubscriptionsTab subscriptions={subscriptions} displayCurrency={displayCurrency} />
        </TabsContent>

        <TabsContent value="investments">
          <InvestmentsTab 
            investments={investments}
            allocation={allocation}
            displayCurrency={displayCurrency}
            onInvestmentBarClick={onInvestmentBarClick}
            onAllocationClick={onAllocationClick}
          />
        </TabsContent>

        <TabsContent value="history">
          <HistoryTab 
            kpiHistory={kpiHistory}
            burnRateSeries={burnRateSeries}
            salarySeries={salarySeries}
            displayCurrency={displayCurrency}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
