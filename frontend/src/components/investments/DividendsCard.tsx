import i18n from "i18next"
import { Trans } from "react-i18next"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { useCallback, useEffect, useState } from "react"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { keepSeriesOrder, numberFormatter } from "@/lib/chartTooltip"
import { Coins, Link2 } from "lucide-react"
import { toast } from "sonner"

import { errorMessage, formatCurrency, formatRate } from "@/lib/utils"
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
import { getAnalyticsDividends } from "@/lib/api/analytics"
import { postInvestmentTransactionsLinkDividends } from "@/lib/api/investments"

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
  return new Date(year, month - 1, 1).toLocaleDateString(appLocale(), { month: "short", year: "2-digit" })
}

const pct = (value: number | null) => formatRate(value)

export function DividendsCard({ accountId, reloadKey, onChanged }: DividendsCardProps) {
  const { t } = useTranslation("investments")
  const [data, setData] = useState<DividendSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<LinkPreview | null>(null)
  const [applying, setApplying] = useState(false)

  const load = useCallback(async () => {
    try {
      setData(await getAnalyticsDividends<DividendSummary>(`?account_id=${accountId}`))
    } catch {
      toast.error(t("dividendsCard.impossibleDeChargerLesDividendes"))
    } finally {
      setLoading(false)
    }
  }, [accountId, t])

  useEffect(() => {
    load()
  }, [load, reloadKey])

  const openLinkPreview = async () => {
    try {
      setPreview(await postInvestmentTransactionsLinkDividends<LinkPreview>(`?account_id=${accountId}&dry_run=true`, {}))
    } catch (err) {
      toast.error(errorMessage(err, t("dividendsCard.erreurLorsDeLAnalyse")))
    }
  }

  const applyLink = async () => {
    setApplying(true)
    try {
      await postInvestmentTransactionsLinkDividends(`?account_id=${accountId}&dry_run=false`, {})
      toast.success(t("dividendsCard.dividendesRattachesALeurTitre"))
      setPreview(null)
      await load()
      onChanged?.()
    } catch (err) {
      toast.error(errorMessage(err, t("dividendsCard.erreurLorsDuRattachement")))
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
      <Card className="shadow-xs">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Coins className="h-5 w-5 text-emerald-600" /> {t("dividendsCard.dividendes")}
          </CardTitle>
          <CardDescription>
            {t("dividendsCard.saisisLeMontantNetRecu")} <Coins className="inline h-3.5 w-3.5 -mt-0.5" /> {t("dividendsCard.dUnePosition")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {unlinked.count > 0 && (
            <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-amber-900">
                <Trans i18n={i18n} ns="investments" i18nKey="misc.unlinked" count={unlinked.count} values={{ total: formatCurrency(unlinked.total_eur) }} components={{ strong: <strong />, amount: <span className="amount-blur" /> }} />
              </p>
              <Button size="sm" variant="outline" className="h-10 gap-2 shrink-0 md:h-9" onClick={openLinkPreview}>
                <Link2 className="h-4 w-4" /> {t("dividendsCard.rattacherAutomatiquement")}
              </Button>
            </div>
          )}

          {!hasDividends ? (
            <p className="py-6 text-center text-sm text-slate-500">{t("dividendsCard.aucunDividendeSaisiSurCe")}</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-4">
                <Kpi label={t("dividendsCard.12DerniersMois")} value={totals.last_12m_eur} />
                <Kpi label={t("dividendsCard.totalRecuNet")} value={totals.net_eur} />
                <Kpi label={t("dividendsCard.totalBrut")} value={totals.gross_eur} />
                <Kpi label={t("dividendsCard.retenuesALaSource")} value={totals.withholding_eur} />
              </div>

              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.by_month} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="month" tickFormatter={monthLabel} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} width={48} tickFormatter={(v) => `${v} €`} />
                    <Tooltip itemSorter={keepSeriesOrder}
                      labelFormatter={(key) => monthLabel(String(key))}
                      formatter={numberFormatter((value: number) => [formatCurrency(value), "Dividendes nets"])}
                      contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                    />
                    <Bar dataKey="net_eur" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Mobile : une carte par titre */}
              <ul className="space-y-2 md:hidden">
                {data.by_ticker.map((row) => (
                  <li key={row.ticker} className="rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="wrap-break-word text-sm font-semibold text-slate-900">{row.asset_name}</div>
                        <div className="font-mono text-[11px] text-slate-500">
                          {row.ticker}
                          {row.last_date && i18n.t("misc.lastDate", { ns: "investments", date: new Date(row.last_date).toLocaleDateString(appLocale()) })}
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className="amount-blur whitespace-nowrap font-mono text-base font-bold tabular-nums">{formatCurrency(row.total_eur)}</div>
                        <div className="text-[11px] text-slate-500">{row.count} versement{row.count > 1 ? "s" : ""}</div>
                      </div>
                    </div>
                    <dl className="mt-2 grid grid-cols-3 gap-2 border-t pt-2 text-xs">
                      <div>
                        <dt className="text-slate-500">{t("dividendsCard.12Mois")}</dt>
                        <dd className="amount-blur whitespace-nowrap font-mono font-medium tabular-nums">{formatCurrency(row.last_12m_eur)}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">{t("dividendsCard.rdtPru")}</dt>
                        <dd className="font-mono font-medium tabular-nums">{pct(row.yield_on_cost_pct)}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">{t("dividendsCard.rdtActuel")}</dt>
                        <dd className="font-mono font-medium tabular-nums">{pct(row.current_yield_pct)}</dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ul>

              <div className="hidden overflow-x-auto md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("dividendsCard.titre")}</TableHead>
                      <TableHead className="text-right">{t("dividendsCard.versements")}</TableHead>
                      <TableHead className="text-right">{t("dividendsCard.totalRecu")}</TableHead>
                      <TableHead className="text-right">{t("dividendsCard.12Mois")}</TableHead>
                      <TableHead className="text-right" title={t("dividendsCard.dividendesDes12DerniersMois")}>{t("dividendsCard.rdtPru")}</TableHead>
                      <TableHead className="text-right" title={t("dividendsCard.dividendesDes12DerniersMois2")}>{t("dividendsCard.rdtActuel")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.by_ticker.map((row) => (
                      <TableRow key={row.ticker}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold text-slate-900">{row.asset_name}</span>
                            <span className="font-mono text-[11px] text-slate-400">
                              {row.ticker}
                              {row.last_date && i18n.t("misc.lastDate", { ns: "investments", date: new Date(row.last_date).toLocaleDateString(appLocale()) })}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">{row.count}</TableCell>
                        <TableCell className="text-right font-mono text-sm font-semibold">
                          <span className="amount-blur">{formatCurrency(row.total_eur)}</span>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          <span className="amount-blur">{formatCurrency(row.last_12m_eur)}</span>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">{pct(row.yield_on_cost_pct)}</TableCell>
                        <TableCell className="text-right font-mono text-sm">{pct(row.current_yield_pct)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex flex-wrap gap-2">
                {data.by_year.map((y) => (
                  <Badge key={y.year} variant="outline" className="gap-2 font-normal">
                    <span className="font-semibold">{y.year}</span>
                    <span className="amount-blur">{i18n.t("misc.netAmount", { ns: "investments", amount: formatCurrency(y.net_eur) })}</span>
                    {y.withholding_eur > 0 && <span className="amount-blur text-slate-400">{i18n.t("misc.grossAmount", { ns: "investments", amount: formatCurrency(y.gross_eur) })}</span>}
                  </Badge>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={preview !== null} onOpenChange={(open) => !open && setPreview(null)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{t("dividendsCard.rattacherLesDividendesALeur")}</DialogTitle>
            <DialogDescription>
              {t("dividendsCard.leTitreEstDeduitDu")}
            </DialogDescription>
          </DialogHeader>
          {preview && (
            <div className="space-y-4 text-sm">
              <div>
                <p className="mb-2 font-semibold text-emerald-700">{i18n.t("misc.toLink", { ns: "investments", count: preview.matched.length })}</p>
                <ul className="space-y-1">
                  {preview.matched.map((m) => (
                    <li key={m.id} className="flex items-center justify-between gap-3 rounded border px-3 py-1.5">
                      <span className="min-w-0 truncate">{m.note || i18n.t("misc.noLabel", { ns: "investments" })}</span>
                      <Badge variant="secondary" className="shrink-0 font-mono">{m.ticker}</Badge>
                    </li>
                  ))}
                </ul>
              </div>
              {preview.unmatched.length > 0 && (
                <div>
                  <p className="mb-2 font-semibold text-slate-600">{i18n.t("misc.unmatched", { ns: "investments", count: preview.unmatched.length })}</p>
                  <ul className="space-y-1">
                    {preview.unmatched.map((u) => (
                      <li key={u.id} className="rounded border border-dashed px-3 py-1.5 text-slate-500">
                        {u.note || i18n.t("misc.noLabel", { ns: "investments" })} • {new Date(u.date).toLocaleDateString(appLocale())}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" className="h-11 sm:h-10" onClick={() => setPreview(null)}>{t("dividendsCard.annuler")}</Button>
            <Button className="h-11 sm:h-10" onClick={applyLink} disabled={applying || !preview || preview.matched.length === 0}>
              {applying ? t("dividendsCard.rattachement") : t("dividendsCard.rattacher")}
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
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 leading-tight">{label}</p>
      <p className="mt-1 whitespace-nowrap text-base font-bold tabular-nums text-slate-900 amount-blur md:text-lg">{formatCurrency(value)}</p>
    </div>
  )
}
