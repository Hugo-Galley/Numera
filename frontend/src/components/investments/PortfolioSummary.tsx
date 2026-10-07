import { useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, Scale } from "lucide-react"
import { toast } from "sonner"

import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { PortfolioRead } from "@/types/portfolio"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

interface PortfolioSummaryProps {
  accountId: number
  /** Change à chaque rechargement des données du compte : relance le calcul */
  reloadKey?: unknown
}

const signed = (value: number) => `${value >= 0 ? "+" : ""}${formatCurrency(value)}`
const tone = (value: number | null) => (value === null ? "text-slate-900" : value >= 0 ? "text-emerald-600" : "text-rose-600")
const pct = (value: number | null) => (value === null ? "-" : `${value >= 0 ? "+" : ""}${value.toFixed(2)} %`)

export function PortfolioSummary({ accountId, reloadKey }: PortfolioSummaryProps) {
  const [data, setData] = useState<PortfolioRead | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .get<PortfolioRead>(`/analytics/portfolio/${accountId}`)
      .then((res) => !cancelled && setData(res))
      .catch(() => !cancelled && toast.error("Impossible de calculer la valeur du portefeuille"))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [accountId, reloadKey])

  if (loading) return <Skeleton className="h-48 w-full rounded-xl" />
  if (!data || !data.valued_by_positions) return null

  const shortPeriod = data.period_days < 365
  const reconciliation = data.reconciliation ?? []
  const latest = reconciliation[reconciliation.length - 1]

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg">Valeur calculée</CardTitle>
        <CardDescription>
          Positions × derniers cours + espèces. Tes relevés servent à vérifier ce calcul, plus à le remplacer.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {(data.warnings.length > 0 || data.stale_tickers.length > 0 || data.lines_without_cost.length > 0) && (
          <div className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            {data.warnings.map((w) => (
              <p key={w} className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{w}</p>
            ))}
            {data.stale_tickers.length > 0 && (
              <p className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                Cours non rafraîchis (dernier cours connu) : {data.stale_tickers.join(", ")}.
              </p>
            )}
            {data.lines_without_cost.length > 0 && (
              <p className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                PRU manquant pour {data.lines_without_cost.join(", ")} : renseigne-le dans le Point Zéro pour voir la plus-value.
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Kpi label="Valeur" value={formatCurrency(data.value, data.currency)} hint={`dont espèces ${formatCurrency(data.cash, data.currency)}`} />
          <Kpi label="Montant investi" value={formatCurrency(data.net_invested, data.currency)} hint="Versements − retraits depuis l'origine" />
          <Kpi
            label="Gain total"
            value={signed(data.gain)}
            hint={pct(data.performance_pct)}
            className={tone(data.gain)}
          />
          <Kpi
            label="Plus-value latente"
            value={data.unrealized_eur === null ? "-" : signed(data.unrealized_eur)}
            hint={
              data.unrealized_eur === null
                ? "PRU inconnu"
                : `${pct(data.unrealized_pct)}${data.fx_effect_eur ? ` · dont change ${signed(data.fx_effect_eur)}` : ""}`
            }
            className={tone(data.unrealized_eur)}
          />
          <Kpi
            label="Plus-value réalisée"
            value={signed(data.realized_eur)}
            hint={data.realized_unknown_sales > 0 ? `${data.realized_unknown_sales} vente(s) sans coût connu` : "Ventes cumulées"}
            className={tone(data.realized_eur)}
          />
          <Kpi label="Dividendes (net)" value={formatCurrency(data.dividends_eur)} hint={`${formatCurrency(data.dividends_12m_eur)} sur 12 mois`} />
          <Kpi label="Frais" value={formatCurrency(data.fees_eur)} hint="Frais de tenue et courtage" />
          <Kpi
            label="XIRR · TWR"
            value={`${data.xirr_pct === null ? "-" : `${data.xirr_pct.toFixed(1)} %`} · ${data.twr_pct === null ? "-" : `${data.twr_pct.toFixed(1)} %`}`}
            hint={shortPeriod ? `Annualisé sur ${data.period_days} j : à relativiser` : "Rendement annualisé · hors effet des versements"}
          />
        </div>

        {data.realized_by_year.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {data.realized_by_year.map((y) => (
              <Badge key={y.year} variant="outline" className="gap-2 font-normal" title={`${y.sales} vente(s), produit ${formatCurrency(y.proceeds_eur)}`}>
                <span className="font-semibold">Réalisé {y.year}</span>
                <span className={`amount-blur ${tone(y.realized_eur)}`}>{signed(y.realized_eur)}</span>
              </Badge>
            ))}
          </div>
        )}

        {latest && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
              <Scale className="h-4 w-4" /> Rapprochement : relevé du courtier vs Numera
              {latest.flagged ? (
                <Badge variant="destructive" className="font-normal">Écart {pct(latest.gap_pct)}</Badge>
              ) : (
                <Badge variant="secondary" className="gap-1 font-normal"><CheckCircle2 className="h-3 w-3" /> Cohérent</Badge>
              )}
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Relevé du</TableHead>
                    <TableHead className="text-right">Relevé</TableHead>
                    <TableHead className="text-right">Numera</TableHead>
                    <TableHead className="text-right">Écart</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[...reconciliation].reverse().slice(0, 5).map((r) => (
                    <TableRow key={r.date}>
                      <TableCell className="text-sm">{new Date(r.date).toLocaleDateString("fr-FR")}</TableCell>
                      <TableCell className="text-right font-mono text-sm"><span className="amount-blur">{formatCurrency(r.snapshot_value, data.currency)}</span></TableCell>
                      <TableCell className="text-right font-mono text-sm"><span className="amount-blur">{formatCurrency(r.computed_value, data.currency)}</span></TableCell>
                      <TableCell className={`text-right font-mono text-sm ${r.flagged ? "font-semibold text-rose-600" : "text-slate-500"}`}>
                        <span className="amount-blur">{signed(r.gap)}</span> ({pct(r.gap_pct)})
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {latest.flagged && (
              <p className="text-xs text-slate-500">
                Un écart de plus de 2 % signale en général une opération, un dividende ou des frais manquants dans l'historique.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Kpi({ label, value, hint, className = "text-slate-900" }: { label: string; value: string; hint?: string; className?: string }) {
  return (
    <div className="rounded-lg border bg-slate-50/60 p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-bold amount-blur ${className}`}>{value}</p>
      {hint && <p className="mt-0.5 text-[11px] text-slate-400">{hint}</p>}
    </div>
  )
}
