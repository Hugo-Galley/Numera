import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useInvestments } from "./useInvestments"
import { InvestmentsKpis } from "./InvestmentsKpis"
import { AccountsAllocation } from "./AccountsAllocation"
import { AssetClassTreemap } from "./AssetClassTreemap"
import { PortfolioBreakdown } from "@/components/investments/PortfolioBreakdown"
import { Concentration } from "@/components/investments/Concentration"
import { EtfCompositions } from "./EtfCompositions"
import { DrillDownDialog } from "./DrillDownDialog"
import { ThirdPartyAccounts } from "./ThirdPartyAccounts"
import { StockPickingBenchmark } from "./StockPickingBenchmark"
import { DrawdownCard } from "./DrawdownCard"

/** Une question par onglet, chaque chiffre à un seul endroit. */
export const INVESTMENT_TABS = ["overview", "performance", "exposure", "funds"] as const
export type InvestmentTab = (typeof INVESTMENT_TABS)[number]

function isTab(value: string | null): value is InvestmentTab {
  return INVESTMENT_TABS.includes(value as InvestmentTab)
}

export default function Investments() {
  const { t } = useTranslation("investments")
  const ctx = useInvestments()
  const [params, setParams] = useSearchParams()
  const requested = params.get("tab")
  const tab: InvestmentTab = isTab(requested) ? requested : "overview"
  const changeTab = (value: string) => {
    const next = new URLSearchParams(params)
    if (value === "overview") next.delete("tab")
    else next.set("tab", value)
    setParams(next, { replace: true })
  }

  if (ctx.loading) return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        <p className="text-slate-500 font-medium">{t("index.chargementDeVosInvestissements")}</p>
      </div>
    </div>
  )

  const hasFunds = (ctx.diversity?.etf_compositions.length ?? 0) > 0

  return (
    <div className="space-y-6 md:space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{t("index.investissements")}</h1>
        <p className="text-sm text-muted-foreground mt-1 md:text-base">{t("index.suivezLaPerformanceEtLa")}</p>
      </div>

      <InvestmentsKpis ctx={ctx} />

      <Tabs value={tab} onValueChange={changeTab} className="space-y-5 md:space-y-6">
        <div className="scroll-fade-x -mx-4 px-4 md:mx-0 md:px-0 overflow-x-auto pb-2 [ms-overflow-style:none] scrollbar-none [&::-webkit-scrollbar]:hidden">
          <TabsList className="bg-slate-50/50 border border-slate-100 p-1 rounded-xl inline-flex w-max">
            {INVESTMENT_TABS.filter((value) => value !== "funds" || hasFunds).map((value) => (
              <TabsTrigger key={value} value={value} className="rounded-lg whitespace-nowrap h-9 px-4 md:h-auto md:px-3">
                {t(`index.tabs.${value}`)}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <TabsContent value="overview" className="space-y-6 md:space-y-8">
          <AccountsAllocation ctx={ctx} />
          <AssetClassTreemap ctx={ctx} />
          <ThirdPartyAccounts />
        </TabsContent>

        <TabsContent value="performance" className="space-y-6 md:space-y-8">
          <DrawdownCard />
          <StockPickingBenchmark />
        </TabsContent>

        <TabsContent value="exposure" className="space-y-6 md:space-y-8">
          {ctx.diversity ? (
            <>
              <PortfolioBreakdown data={ctx.diversity} scope="portfolio" />
              <Concentration data={ctx.diversity} onReferenceChange={() => void ctx.reloadDiversity()} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">{t("index.exposureUnavailable")}</p>
          )}
        </TabsContent>

        {hasFunds && (
          <TabsContent value="funds">
            <EtfCompositions ctx={ctx} />
          </TabsContent>
        )}
      </Tabs>

      <DrillDownDialog ctx={ctx} />
    </div>
  )
}
