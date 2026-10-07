import { formatCurrency } from "@/lib/utils"
import type { PortfolioOverview } from "@/types/portfolio"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const signed = (value: number) => `${value >= 0 ? "+" : ""}${formatCurrency(value)}`
const tone = (value: number | null) => (value === null ? "text-slate-900" : value >= 0 ? "text-emerald-600" : "text-rose-600")

export function PortfolioOverviewCard({ data }: { data: PortfolioOverview }) {
  const stats = [
    { label: "Plus-value latente", value: data.unrealized_eur === null ? "-" : signed(data.unrealized_eur), color: tone(data.unrealized_eur), hint: "Comptes titres, coût aux taux des achats" },
    { label: "Plus-value réalisée", value: signed(data.realized_eur), color: tone(data.realized_eur), hint: "Ventes cumulées" },
    { label: "Dividendes (net)", value: formatCurrency(data.dividends_eur), color: "text-slate-900", hint: `${formatCurrency(data.dividends_12m_eur)} sur 12 mois` },
    { label: "XIRR global", value: data.xirr_pct === null ? "-" : `${data.xirr_pct.toFixed(1)} %`, color: tone(data.xirr_pct), hint: "Rendement annualisé pondéré par tes versements" },
    { label: "Frais", value: formatCurrency(data.fees_eur), color: "text-slate-900", hint: "Tenue de compte et courtage" },
  ]

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg">Plus-values et rendement</CardTitle>
        <CardDescription>
          Comptes titres valorisés par leurs positions ({data.accounts.length}). Le détail et le rapprochement avec tes relevés sont sur chaque compte.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {stats.map((s) => (
            <div key={s.label} className="rounded-lg border bg-slate-50/60 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{s.label}</p>
              <p className={`mt-1 text-lg font-bold amount-blur ${s.color}`}>{s.value}</p>
              <p className="mt-0.5 text-[11px] text-slate-400">{s.hint}</p>
            </div>
          ))}
        </div>
        {data.realized_by_year.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Réalisé par année</span>
            {data.realized_by_year.map((y) => (
              <Badge key={y.year} variant="outline" className="gap-2 font-normal" title={`${y.sales} vente(s), produit ${formatCurrency(y.proceeds_eur)}`}>
                <span className="font-semibold">{y.year}</span>
                <span className={`amount-blur ${tone(y.realized_eur)}`}>{signed(y.realized_eur)}</span>
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
