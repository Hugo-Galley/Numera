import { Trans, useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ChevronDown } from "lucide-react"
import { Input } from "@/components/ui/input"
import { cn, formatCurrency, formatRate } from "@/lib/utils"
import { Step } from "./forecastParts"
import { TYPE_LABELS } from "./types"
import type { WealthForecastView } from "./useWealthForecast"

/** Méthode de calcul détaillée (repliable). */
export function ForecastMethodCard({ ctx }: { ctx: WealthForecastView }) {
  const { t } = useTranslation("tools")
  const { boostedShown, data, investInput, otherInput, savingsInput, setInvestInput, setOtherInput, setSavingsInput, setShowMethod, setShowMonths, showMethod, showMonths } = ctx
  return (
    <>
      <Card className="shadow-sm border-slate-100">
        <button
          type="button"
          className="flex w-full items-center justify-between gap-3 p-6 text-left"
          onClick={() => setShowMethod((v) => !v)}
          aria-expanded={showMethod}
        >
          <div className="space-y-1">
            <p className="text-lg font-semibold text-slate-900">{t("forecastMethodCard.commentCEstCalcule")}</p>
            <p className="text-sm text-slate-500">{t("forecastMethodCard.les3HypothesesDeLa")}</p>
          </div>
          <ChevronDown className={cn("h-5 w-5 shrink-0 text-slate-400 transition-transform", showMethod && "rotate-180")} />
        </button>
        {showMethod && (
          <CardContent className="space-y-6 pt-0">
            <Step n={1} title={t("forecastMethodCard.tonPointDeDepart")}>
              <p>
                <Trans t={t} i18nKey="misc.startWealth" values={{ amount: formatCurrency(data.current_wealth, "EUR") }} components={{ b: <b className="text-slate-900 amount-blur" /> }} />
              </p>
            </Step>

            <Step n={2} title={t("forecastMethodCard.ceQueTuMetsDe")}>
              <p>
                {t("forecastMethodCard.cEstCeQuIl")} <b>{t("forecastMethodCard.revenusDepenses")}</b>. {t("misc.savingsNote")}
                {data.months_used > 0 && <> {t("misc.avgLastMonths", { count: data.months_used })}</>}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-slate-700">{t("forecastMethodCard.montantUtilise")}</span>
                <Input
                  type="number" inputMode="decimal"
                  className="h-10 w-28 md:h-9"
                  placeholder={String(Math.round(data.computed_monthly_savings))}
                  value={savingsInput}
                  onChange={(e) => setSavingsInput(e.target.value)}
                />
                <span className="text-slate-500">{t("forecastMethodCard.mois")}</span>
                {data.savings_overridden ? (
                  <Button size="sm" variant="ghost" onClick={() => setSavingsInput("")}>
                    {t("misc.backToCalc", { amount: formatCurrency(data.computed_monthly_savings, "EUR") })}
                  </Button>
                ) : (
                  <span className="text-xs text-slate-400">{t("forecastMethodCard.calculeAutomatiquementSaisisUnMontant")}</span>
                )}
              </div>
              {data.savings_months.length > 0 && (
                <>
                  <button
                    type="button"
                    className="text-xs font-medium text-blue-600 hover:underline"
                    onClick={() => setShowMonths((v) => !v)}
                  >
                    {showMonths ? t("forecastMethodCard.masquerLeDetailMoisPar") : t("forecastMethodCard.voirLeDetailMoisPar")}
                  </button>
                  {showMonths && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs tabular-nums">
                        <thead>
                          <tr className="text-left text-slate-500">
                            <th className="py-1 pr-3 font-medium">{t("forecastMethodCard.mois2")}</th>
                            <th className="py-1 pr-3 text-right font-medium">{t("forecastMethodCard.revenus")}</th>
                            <th className="py-1 pr-3 text-right font-medium">{t("forecastMethodCard.depenses")}</th>
                            <th className="py-1 text-right font-medium">{t("forecastMethodCard.reste")}</th>
                          </tr>
                        </thead>
                        <tbody className="amount-blur">
                          {data.savings_months.map((m) => (
                            <tr key={m.label} className="border-t border-slate-100">
                              <td className="py-1 pr-3">{m.label}</td>
                              <td className="py-1 pr-3 text-right">{formatCurrency(m.revenus, "EUR")}</td>
                              <td className="py-1 pr-3 text-right">{formatCurrency(m.depenses_reelles, "EUR")}</td>
                              <td className="py-1 text-right font-semibold">{formatCurrency(m.epargne_flow, "EUR")}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </Step>

            <Step n={3} title={t("forecastMethodCard.ceQueTonArgentRapporte")}>
              <p>
                {t("forecastMethodCard.chaqueGroupeDeComptesA")}
              </p>
              <div className="divide-y divide-slate-100 rounded-lg border border-slate-100">
                {data.return_breakdown.map((r) => {
                  const isInvest = r.type.startsWith("investissement")
                  const value = isInvest ? investInput : otherInput
                  const setValue = isInvest ? setInvestInput : setOtherInput
                  return (
                    <div key={r.type} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2">
                      <div className="min-w-0 flex-1 basis-40">
                        <p className="text-slate-700">{TYPE_LABELS[r.type] ?? r.type}</p>
                        <p className="text-xs tabular-nums text-slate-400">
                          <span className="amount-blur">{formatCurrency(r.balance, "EUR")}</span>
                          {" · "}
                          {r.source === "manual" ? t("misc.rateManual") : r.source === "observed" ? t("misc.rateObserved") : t("misc.rateNone")}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          type="number" inputMode="decimal"
                          className="h-10 w-20 md:h-9"
                          placeholder={r.rate_pct.toFixed(1)}
                          value={value}
                          onChange={(e) => setValue(e.target.value)}
                        />
                        <span className="text-slate-500">{t("forecastMethodCard.an")}</span>
                        {r.source === "manual" && (
                          <Button size="sm" variant="ghost" onClick={() => setValue("")}>
                            {t("misc.backTo", { rate: isInvest && data.observed_investment_return_pct !== null ? formatRate(data.observed_investment_return_pct, 1) : t("forecastMethodCard.0") })}
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
              <p>
                {t("forecastMethodCard.tauxGlobalRetenu")} <b className="text-slate-900">{formatRate(data.annual_return_pct, 1)}</b> {t("forecastMethodCard.parAnLesComptesLes")}
              </p>
            </Step>

            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
              <p className="font-medium text-slate-700">{t("forecastMethodCard.ensuiteMoisApresMois")}</p>
              <p>
                {t("forecastMethodCard.onPartDuPointDe")}
                {boostedShown ? t("misc.boostedNote", { amount: data.extra_monthly }) : ""}{t("misc.repeatFor", { years: data.years })}
              </p>
            </div>
          </CardContent>
        )}
      </Card>
    </>
  )
}
