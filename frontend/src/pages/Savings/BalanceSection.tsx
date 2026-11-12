import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Eye, PiggyBank, ShieldCheck, Target, TrendingUp } from "lucide-react"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { SavingsCtx } from "./useSavings"

/** Section 1 : bilan financier. */
export function BalanceSection({ ctx }: { ctx: SavingsCtx }) {
  const { t } = useTranslation("savings")
  const { analytics, getRateColor, hasIncome, resilience, savingsRate } = ctx
  return (
    <>
      {/* SECTION 1 : BILAN FINANCIER */}
      <section className="space-y-4 md:space-y-6">
        <div className="flex items-center gap-2 border-b pb-2">
          <Eye className="h-5 w-5 text-slate-400" />
          <h2 className="text-xl font-bold text-slate-900">{t("balanceSection.bilanFinancier")}</h2>
        </div>

        <div className="grid gap-3 grid-cols-2 md:gap-6 lg:grid-cols-4">
          <Card className="theme-island col-span-2 shadow-sm border-slate-200 bg-slate-900 md:col-span-1 text-white hover:shadow-md transition-shadow">
            <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2 space-y-0 p-4 md:p-6 md:pb-2">
              <CardDescription className="font-medium text-slate-300">{t("balanceSection.patrimoineNetTotal")}</CardDescription>
              <div className="h-10 w-10 bg-white/10 rounded-xl flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-white" />
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0 md:p-6 md:pt-0">
              <CardTitle className="text-2xl sm:text-3xl font-black">
                {formatCurrency(analytics?.patrimoine_net_total || 0)}
              </CardTitle>
              <p className="text-xs text-slate-400 mt-2">{t("balanceSection.actifsLiquidesInvestissements")}</p>
            </CardContent>
          </Card>

          <Card className="col-span-2 shadow-sm border-slate-100 hover:border-emerald-200 transition-colors md:col-span-1">
            <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2 space-y-0 p-4 md:p-6 md:pb-2">
              <CardDescription className="font-medium">{t("balanceSection.epargneLiquide")}</CardDescription>
              <div className="h-10 w-10 bg-emerald-50 rounded-xl flex items-center justify-center">
                <PiggyBank className="h-5 w-5 text-emerald-600" />
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0 md:p-6 md:pt-0">
              <CardTitle className="text-2xl sm:text-3xl font-bold text-emerald-600 amount-blur">
                {formatCurrency(analytics?.epargne_total || 0)}
              </CardTitle>
              <p className="text-xs text-slate-500 mt-2">{t("balanceSection.disponibleImmediatement")}</p>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-100 hover:border-blue-200 transition-colors">
            <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2 space-y-0 p-4 md:p-6 md:pb-2">
              <CardDescription className="font-medium">{t("balanceSection.tauxDEpargne")}</CardDescription>
              <div className="h-10 w-10 bg-blue-50 rounded-xl flex items-center justify-center">
                <Target className="h-5 w-5 text-blue-600" />
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0 md:p-6 md:pt-0">
              <CardTitle className={`text-2xl sm:text-3xl font-bold ${hasIncome ? getRateColor(savingsRate) : "text-slate-400"}`}>
                {/* Le backend borne le taux à ±100 % : afficher « −100 % » ferait croire à une valeur exacte */}
                {!hasIncome ? "—" : savingsRate <= -100 ? "≤ −100 %" : formatRate(savingsRate, 1)}
              </CardTitle>
              {!hasIncome && <p className="text-xs text-slate-500 mt-1">{t("balanceSection.aucunRevenuSurLaPeriode")}</p>}
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-600 transition-all duration-1000" 
                    style={{ width: `${Math.min(100, savingsRate)}%` }} 
                  />
                </div>
                <span className="text-[10px] text-slate-400 font-medium">{t("balanceSection.objectif20")}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-100 hover:border-slate-200 transition-colors">
            <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2 space-y-0 p-4 md:p-6 md:pb-2">
              <CardDescription className="font-medium">{t("balanceSection.indiceResilience")}</CardDescription>
              <div className="h-10 w-10 bg-slate-50 rounded-xl flex items-center justify-center">
                <ShieldCheck className="h-5 w-5 text-slate-600" />
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0 md:p-6 md:pt-0">
              <CardTitle className="text-2xl sm:text-3xl font-bold text-slate-900">
                {resilience?.months != null ? i18n.t("misc.monthsValue", { ns: "savings", value: resilience.months.toLocaleString(appLocale(), { maximumFractionDigits: 1 }) }) : "—"}
              </CardTitle>
              <p className="text-xs text-slate-500 mt-2">
                {resilience?.months != null
                  ? i18n.t("misc.resilienceHint", { ns: "savings", count: resilience.months_used })
                  : t("balanceSection.pasEncoreDeMoisComplet")}
              </p>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  )
}
