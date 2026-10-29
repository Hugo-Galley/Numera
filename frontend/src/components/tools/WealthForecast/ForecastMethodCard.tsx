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
  const { boostedShown, data, investInput, otherInput, savingsInput, setInvestInput, setOtherInput, setSavingsInput, setShowMethod, setShowMonths, showMethod, showMonths, years } = ctx
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
            <p className="text-lg font-semibold text-slate-900">Comment c'est calculé</p>
            <p className="text-sm text-slate-500">Les 3 hypothèses de la prévision, et comment les modifier.</p>
          </div>
          <ChevronDown className={cn("h-5 w-5 shrink-0 text-slate-400 transition-transform", showMethod && "rotate-180")} />
        </button>
        {showMethod && (
          <CardContent className="space-y-6 pt-0">
            <Step n={1} title="Ton point de départ">
              <p>
                Ce que valent tous tes comptes aujourd'hui (courant, épargne et investissements) :{" "}
                <b className="text-slate-900 amount-blur">{formatCurrency(data.current_wealth, "EUR")}</b>.
              </p>
            </Step>

            <Step n={2} title="Ce que tu mets de côté chaque mois">
              <p>
                C'est ce qu'il te reste en fin de mois : <b>revenus − dépenses</b>. Les virements vers ton épargne ou
                tes investissements ne sont pas des dépenses (l'argent reste à toi), ils ne sont donc pas retirés.
                {data.months_used > 0 && <> Moyenne des {data.months_used} derniers mois.</>}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-slate-700">Montant utilisé :</span>
                <Input
                  type="number" inputMode="decimal"
                  className="h-10 w-28 md:h-9"
                  placeholder={String(Math.round(data.computed_monthly_savings))}
                  value={savingsInput}
                  onChange={(e) => setSavingsInput(e.target.value)}
                />
                <span className="text-slate-500">€/mois</span>
                {data.savings_overridden ? (
                  <Button size="sm" variant="ghost" onClick={() => setSavingsInput("")}>
                    Revenir au calcul ({formatCurrency(data.computed_monthly_savings, "EUR")})
                  </Button>
                ) : (
                  <span className="text-xs text-slate-400">calculé automatiquement, saisis un montant pour le remplacer</span>
                )}
              </div>
              {data.savings_months.length > 0 && (
                <>
                  <button
                    type="button"
                    className="text-xs font-medium text-blue-600 hover:underline"
                    onClick={() => setShowMonths((v) => !v)}
                  >
                    {showMonths ? "Masquer le détail mois par mois" : "Voir le détail mois par mois"}
                  </button>
                  {showMonths && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs tabular-nums">
                        <thead>
                          <tr className="text-left text-slate-500">
                            <th className="py-1 pr-3 font-medium">Mois</th>
                            <th className="py-1 pr-3 text-right font-medium">Revenus</th>
                            <th className="py-1 pr-3 text-right font-medium">Dépenses</th>
                            <th className="py-1 text-right font-medium">Reste</th>
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

            <Step n={3} title="Ce que ton argent rapporte chaque année">
              <p>
                Chaque groupe de comptes a son propre taux. Pour tes investissements, c'est la performance réellement
                mesurée sur tes comptes titres. Là où rien n'est mesurable (courant, épargne, comptes suivis par
                simple relevé), on compte 0 % : saisis un taux si tu veux en tenir compte.
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
                          {r.source === "manual" ? "taux saisi" : r.source === "observed" ? "taux mesuré" : "non mesuré"}
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
                        <span className="text-slate-500">%/an</span>
                        {r.source === "manual" && (
                          <Button size="sm" variant="ghost" onClick={() => setValue("")}>
                            Revenir à {isInvest && data.observed_investment_return_pct !== null ? formatRate(data.observed_investment_return_pct, 1) : "0 %"}
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
              <p>
                Taux global retenu : <b className="text-slate-900">{formatRate(data.annual_return_pct, 1)}</b> par an
                (les comptes les plus gros pèsent le plus).
              </p>
            </Step>

            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
              <p className="font-medium text-slate-700">Ensuite, mois après mois</p>
              <p>
                On part du point de départ, on ajoute ce que ton argent a rapporté, puis ce que tu mets de côté
                {boostedShown ? ` (+${data.extra_monthly} € pour la courbe verte)` : ""}. On répète pendant {data.years} ans.
              </p>
            </div>
          </CardContent>
        )}
      </Card>
    </>
  )
}
