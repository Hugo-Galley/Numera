import { useCallback, useEffect, useState } from "react"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Coins, Link2 } from "lucide-react"
import { toast } from "sonner"

import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

interface DividendSummary {
  totals: { count: number; net_eur: number; withholding_eur: number; gross_eur: number; last_12m_eur: number }
  by_month: { month: string; net_eur: number }[]
  by_year: { year: number; count: number; net_eur: number; withholding_eur: number; gross_eur: number }[]
  by_ticker: {
    ticker: string
    asset_name: string
    count: number
    total_eur: number
    last_12m_eur: number
    last_date: string | null
    yield_on_cost_pct: number | null
    current_yield_pct: number | null
  }[]
  unlinked: { count: number; total_eur: number }
}

interface LinkedDividend {
  id: number
  date: string
  note: string | null
  amount: number
  currency: string
  ticker?: string
}

interface LinkPreview {
  applied: boolean
  matched: LinkedDividend[]
  unmatched: LinkedDividend[]
}

interface DividendsCardProps {
  accountId: number
  /** Change à chaque rechargement des données du compte : relance le calcul */
  reloadKey?: unknown
  onChanged?: () => void
}

const monthLabel = (key: string) => {
  const [year, month] = key.split("-").map(Number)
  return new Date(year, month - 1, 1).toLocaleDateString("fr-FR", { month: "short", year: "2-digit" })
}

const pct = (value: number | null) => (value === null ? "-" : `${value.toFixed(2)} %`)

export function DividendsCard({ accountId, reloadKey, onChanged }: DividendsCardProps) {
  const [data, setData] = useState<DividendSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<LinkPreview | null>(null)
  const [applying, setApplying] = useState(false)

  const load = useCallback(async () => {
    try {
      setData(await api.get<DividendSummary>(`/analytics/dividends?account_id=${accountId}`))
    } catch {
      toast.error("Impossible de charger les dividendes")
    } finally {
      setLoading(false)
    }
  }, [accountId])

  useEffect(() => {
    load()
  }, [load, reloadKey])

  const openLinkPreview = async () => {
    try {
      setPreview(await api.post<LinkPreview>(`/investment-transactions/link-dividends?account_id=${accountId}&dry_run=true`, {}))
    } catch (err: any) {
      toast.error(err?.message || "Erreur lors de l'analyse des dividendes")
    }
  }

  const applyLink = async () => {
    setApplying(true)
    try {
      await api.post(`/investment-transactions/link-dividends?account_id=${accountId}&dry_run=false`, {})
      toast.success("Dividendes rattachés à leur titre")
      setPreview(null)
      await load()
      onChanged?.()
    } catch (err: any) {
      toast.error(err?.message || "Erreur lors du rattachement")
    } finally {
      setApplying(false)
    }
  }

  if (loading) return <Skeleton className="h-64 w-full rounded-xl" />
  if (!data) return null

  const { totals, unlinked } = data
  const hasDividends = totals.count > 0

  return (
    <>
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Coins className="h-5 w-5 text-emerald-600" /> Dividendes
          </CardTitle>
          <CardDescription>
            Saisis le montant net reçu (celui de ton courtier) avec le bouton <Coins className="inline h-3.5 w-3.5 -mt-0.5" /> d'une position.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {unlinked.count > 0 && (
            <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-amber-900">
                <strong>{unlinked.count} dividende{unlinked.count > 1 ? "s" : ""}</strong> (
                <span className="amount-blur">{formatCurrency(unlinked.total_eur)}</span>) ne {unlinked.count > 1 ? "sont" : "est"} rattaché
                {unlinked.count > 1 ? "s" : ""} à aucun titre : le rendement par ligne est incomplet.
              </p>
              <Button size="sm" variant="outline" className="gap-2 shrink-0" onClick={openLinkPreview}>
                <Link2 className="h-4 w-4" /> Rattacher automatiquement
              </Button>
            </div>
          )}

          {!hasDividends ? (
            <p className="py-6 text-center text-sm text-slate-500">Aucun dividende saisi sur ce compte.</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <Kpi label="12 derniers mois" value={totals.last_12m_eur} />
                <Kpi label="Total reçu (net)" value={totals.net_eur} />
                <Kpi label="Total brut" value={totals.gross_eur} />
                <Kpi label="Retenues à la source" value={totals.withholding_eur} />
              </div>

              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.by_month} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="month" tickFormatter={monthLabel} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} width={48} tickFormatter={(v) => `${v} €`} />
                    <Tooltip
                      labelFormatter={(key) => monthLabel(String(key))}
                      formatter={(value: number) => [formatCurrency(value), "Dividendes nets"]}
                      contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                    />
                    <Bar dataKey="net_eur" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Titre</TableHead>
                      <TableHead className="text-right">Versements</TableHead>
                      <TableHead className="text-right">Total reçu</TableHead>
                      <TableHead className="text-right">12 mois</TableHead>
                      <TableHead className="text-right" title="Dividendes des 12 derniers mois ÷ coût de revient">Rdt / PRU</TableHead>
                      <TableHead className="text-right" title="Dividendes des 12 derniers mois ÷ valeur actuelle">Rdt actuel</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.by_ticker.map((t) => (
                      <TableRow key={t.ticker}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold text-slate-900">{t.asset_name}</span>
                            <span className="font-mono text-[11px] text-slate-400">
                              {t.ticker}
                              {t.last_date && ` • dernier : ${new Date(t.last_date).toLocaleDateString("fr-FR")}`}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">{t.count}</TableCell>
                        <TableCell className="text-right font-mono text-sm font-semibold">
                          <span className="amount-blur">{formatCurrency(t.total_eur)}</span>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          <span className="amount-blur">{formatCurrency(t.last_12m_eur)}</span>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">{pct(t.yield_on_cost_pct)}</TableCell>
                        <TableCell className="text-right font-mono text-sm">{pct(t.current_yield_pct)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex flex-wrap gap-2">
                {data.by_year.map((y) => (
                  <Badge key={y.year} variant="outline" className="gap-2 font-normal">
                    <span className="font-semibold">{y.year}</span>
                    <span className="amount-blur">{formatCurrency(y.net_eur)} net</span>
                    {y.withholding_eur > 0 && <span className="amount-blur text-slate-400">({formatCurrency(y.gross_eur)} brut)</span>}
                  </Badge>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={preview !== null} onOpenChange={(open) => !open && setPreview(null)}>
        <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Rattacher les dividendes à leur titre</DialogTitle>
            <DialogDescription>
              Le titre est déduit du libellé (« Dividende Apple » → AAPL). Rien n'est modifié avant que tu valides.
            </DialogDescription>
          </DialogHeader>
          {preview && (
            <div className="space-y-4 text-sm">
              <div>
                <p className="mb-2 font-semibold text-emerald-700">{preview.matched.length} à rattacher</p>
                <ul className="space-y-1">
                  {preview.matched.map((m) => (
                    <li key={m.id} className="flex items-center justify-between gap-3 rounded border px-3 py-1.5">
                      <span className="truncate">{m.note || "(sans libellé)"}</span>
                      <Badge variant="secondary" className="font-mono">{m.ticker}</Badge>
                    </li>
                  ))}
                </ul>
              </div>
              {preview.unmatched.length > 0 && (
                <div>
                  <p className="mb-2 font-semibold text-slate-600">{preview.unmatched.length} non reconnu{preview.unmatched.length > 1 ? "s" : ""} (à modifier à la main)</p>
                  <ul className="space-y-1">
                    {preview.unmatched.map((u) => (
                      <li key={u.id} className="rounded border border-dashed px-3 py-1.5 text-slate-500">
                        {u.note || "(sans libellé)"} • {new Date(u.date).toLocaleDateString("fr-FR")}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPreview(null)}>Annuler</Button>
            <Button onClick={applyLink} disabled={applying || !preview || preview.matched.length === 0}>
              {applying ? "Rattachement..." : "Rattacher"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function Kpi({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-slate-50/60 p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-slate-900 amount-blur">{formatCurrency(value)}</p>
    </div>
  )
}
