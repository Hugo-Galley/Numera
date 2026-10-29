import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { formatCurrency, formatRate } from "@/lib/utils"
import { EXTRA_PRESETS, HORIZONS } from "./forecastParts"
import type { WealthForecastView } from "./useWealthForecast"

/** Montant projeté, répartition, horizon et versement en plus. */
export function ForecastSummaryCard({ ctx }: { ctx: WealthForecastView }) {
  const { boostedShown, data, extra, final, setExtra, setYears, years } = ctx
  return (
    <>
      <Card className="shadow-sm border-slate-100">
        <CardHeader>
          <CardDescription>Dans {data.years} ans, tu auras environ</CardDescription>
          <CardTitle className="text-4xl sm:text-5xl font-black tracking-tight tabular-nums text-slate-900 amount-blur">
            {formatCurrency(final, "EUR")}
          </CardTitle>
          {boostedShown && (
            <p className="text-sm font-bold text-emerald-600 amount-blur">
              {data.gain_from_extra >= 0 ? "+" : ""}
              {formatCurrency(data.gain_from_extra, "EUR")} grâce à {data.extra_monthly > 0 ? "+" : ""}
              {data.extra_monthly} €/mois
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div className="rounded-lg bg-slate-50 px-3 py-2">
              <p className="text-xs text-slate-500">Tu pars de</p>
              <p className="font-bold tabular-nums text-slate-900 amount-blur">{formatCurrency(data.current_wealth, "EUR")}</p>
            </div>
            <div className="rounded-lg bg-slate-50 px-3 py-2">
              <p className="text-xs text-slate-500">Tu mets de côté{data.savings_overridden ? " (saisi)" : ""}</p>
              <p className="font-bold tabular-nums text-slate-900 amount-blur">
                {formatCurrency(data.avg_monthly_savings, "EUR")}
                <span className="text-xs font-normal text-slate-500"> /mois</span>
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 px-3 py-2">
              <p className="text-xs text-slate-500">
                Ton argent rapporte{data.return_breakdown.some((r) => r.source === "manual") ? " (en partie saisi)" : ""}
              </p>
              <p className="font-bold tabular-nums text-slate-900 amount-blur">
                {formatRate(data.annual_return_pct, 1)}
                <span className="text-xs font-normal text-slate-500"> /an</span>
              </p>
            </div>
          </div>
          {data.avg_monthly_savings < 0 && (
            <p className="text-sm font-medium text-amber-600">
              Tu dépenses plus que tu ne gagnes en moyenne : le patrimoine diminue dans cette prévision.
            </p>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 w-full text-sm font-medium text-slate-700 sm:w-auto">J'épargne en plus :</span>
            {EXTRA_PRESETS.map((v) => (
              <Button
                key={v}
                size="sm"
                className="h-10 md:h-9"
                variant={extra === v ? "default" : "outline"}
                onClick={() => setExtra(v)}
              >
                {v === 0 ? "Rien" : `+${v} €`}
              </Button>
            ))}
            <Input
              type="number" inputMode="decimal"
              className="h-10 w-28 md:h-9"
              placeholder="Autre"
              value={EXTRA_PRESETS.includes(extra) ? "" : extra}
              onChange={(e) => setExtra(Number(e.target.value) || 0)}
            />
            <span className="text-sm text-slate-500">€/mois</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 w-full text-sm font-medium text-slate-700 sm:w-auto">Horizon :</span>
            {HORIZONS.map((h) => (
              <Button key={h} size="sm" className="h-10 flex-1 sm:flex-none md:h-9" variant={years === h ? "default" : "outline"} onClick={() => setYears(h)}>
                {h} ans
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  )
}
