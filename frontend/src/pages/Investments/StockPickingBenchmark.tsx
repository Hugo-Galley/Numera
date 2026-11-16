import { useEffect, useEffectEvent, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { AlertTriangle, Scale } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { getAnalyticsStockPickingBenchmark, putAnalyticsStockPickingBenchmarkReference } from "@/lib/api/investments"
import type { ApiResponse } from "@/lib/api/types"
import { formatCurrency, formatRate } from "@/lib/utils"
import { appLocale } from "@/i18n/locale"

type Benchmark = ApiResponse<"/analytics/stock-picking-benchmark", "get">

const AUTO = "__auto__"
const signed = (value: number) => `${value >= 0 ? "+" : ""}${formatCurrency(value)}`
const tone = (value: number | null | undefined) => (value == null ? "text-slate-500" : value >= 0 ? "text-emerald-600" : "text-rose-600")
const day = (iso: string | null | undefined) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(appLocale()) : "-")

/** Stock picking (titres hors ETF) face au même argent placé aux mêmes dates dans un indice de référence. */
export function StockPickingBenchmark() {
  const { t } = useTranslation("investments")
  const [data, setData] = useState<Benchmark | null>(null)
  const [failed, setFailed] = useState(false)
  const [custom, setCustom] = useState("")
  const [saving, setSaving] = useState(false)

  const load = async () => {
    try {
      setData(await getAnalyticsStockPickingBenchmark())
      setFailed(false)
    } catch {
      setFailed(true)
    }
  }
  const loadOnMount = useEffectEvent(() => { void load() })
  useEffect(() => { loadOnMount() }, [])

  const choose = async (ticker: string | null) => {
    setSaving(true)
    try {
      await putAnalyticsStockPickingBenchmarkReference({ ticker })
      setCustom("")
      await load()
    } catch {
      toast.error(t("benchmark.saveError"))
    } finally {
      setSaving(false)
    }
  }

  if (failed || !data) return null
  const lines = data.lines ?? []
  const candidates = data.candidates ?? []
  if (lines.length === 0 && data.benchmark_ticker == null) return null

  const selected = data.benchmark_source === "largest_etf" ? AUTO : (data.benchmark_ticker ?? AUTO)
  const options = candidates.some((c) => c.ticker === data.benchmark_ticker) || !data.benchmark_ticker
    ? candidates
    : [...candidates, { ticker: data.benchmark_ticker, name: data.benchmark_name ?? data.benchmark_ticker }]

  return (
    <Card data-testid="stock-picking-benchmark">
      <CardHeader className="gap-3 md:flex md:flex-row md:items-start md:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Scale className="h-5 w-5 text-slate-700" />
            {t("benchmark.title", { name: data.benchmark_name ?? data.benchmark_ticker ?? "" })}
          </CardTitle>
          <CardDescription>{data.start_date ? t("benchmark.subtitle", { date: day(data.start_date) }) : t("benchmark.subtitleNoDate")}</CardDescription>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={selected} onValueChange={(value) => void choose(value === AUTO ? null : value)} disabled={saving}>
            <SelectTrigger className="w-56" aria-label={t("benchmark.reference")}><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={AUTO}>{t("benchmark.auto")}</SelectItem>
              {options.map((c) => <SelectItem key={c.ticker} value={c.ticker}>{c.name} ({c.ticker})</SelectItem>)}
            </SelectContent>
          </Select>
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (custom.trim()) void choose(custom.trim()) }}>
            <Input value={custom} onChange={(e) => setCustom(e.target.value)} placeholder={t("benchmark.otherTicker")} className="w-32" aria-label={t("benchmark.otherTicker")} />
            <Button type="submit" variant="outline" disabled={saving || !custom.trim()}>{t("benchmark.apply")}</Button>
          </form>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {lines.length > 0 && <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-200 p-3">
            <p className="text-xs text-slate-500">{t("benchmark.gap")}</p>
            <p className={`text-2xl font-black tabular-nums ${tone(data.gap_eur)}`}>{data.gap_eur != null ? signed(data.gap_eur) : "-"}</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-3">
            <p className="text-xs text-slate-500">{t("benchmark.stocksSide")}</p>
            <p className="text-lg font-bold tabular-nums">{data.stock_total_eur != null ? formatCurrency(data.stock_total_eur) : "-"}</p>
            <p className="text-xs text-slate-500">{t("benchmark.xirr", { rate: formatRate(data.stock_xirr_pct, 1, true) })}</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-3">
            <p className="text-xs text-slate-500">{t("benchmark.referenceSide", { ticker: data.benchmark_ticker ?? "" })}</p>
            <p className="text-lg font-bold tabular-nums">{data.benchmark_total_eur != null ? formatCurrency(data.benchmark_total_eur) : "-"}</p>
            <p className="text-xs text-slate-500">{t("benchmark.xirr", { rate: formatRate(data.benchmark_xirr_pct, 1, true) })}</p>
          </div>
        </div>}

        {(data.warnings ?? []).map((warning) => (
          <p key={warning} className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-sm text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{warning}
          </p>
        ))}

        {lines.length === 0 ? (
          <p className="text-sm text-slate-500">{t("benchmark.empty")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-slate-500">
                  <th className="py-2 pr-2 font-medium">{t("benchmark.line")}</th>
                  <th className="hidden py-2 pr-2 text-right font-medium md:table-cell">{t("benchmark.invested")}</th>
                  <th className="py-2 pr-2 text-right font-medium">{t("benchmark.stocks")}</th>
                  <th className="py-2 pr-2 text-right font-medium">{t("benchmark.referenceColumn")}</th>
                  <th className="py-2 pr-2 text-right font-medium">{t("benchmark.gapColumn")}</th>
                  <th className="hidden py-2 text-right font-medium sm:table-cell">{t("benchmark.xirrColumn")}</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line) => (
                  <tr key={`${line.account_id}-${line.ticker}`} className="border-b last:border-0">
                    <td className="py-2 pr-2">
                      <span className="font-semibold text-slate-900">{line.asset_name}</span>
                      <span className="ml-1 text-xs text-slate-500">{line.ticker} · {line.account_name}</span>
                      {line.missing_price && <Badge variant="secondary" className="ml-2 border-amber-200 bg-amber-50 text-amber-700">{t("benchmark.missingPrice")}</Badge>}
                    </td>
                    <td className="hidden py-2 pr-2 text-right tabular-nums md:table-cell">{formatCurrency(line.invested_eur ?? 0)}</td>
                    <td className="py-2 pr-2 text-right tabular-nums">{line.stock_total_eur != null ? formatCurrency(line.stock_total_eur) : "-"}</td>
                    <td className="py-2 pr-2 text-right tabular-nums">{line.benchmark_total_eur != null ? formatCurrency(line.benchmark_total_eur) : "-"}</td>
                    <td className={`py-2 pr-2 text-right font-semibold tabular-nums ${tone(line.gap_eur)}`}>{line.gap_eur != null ? signed(line.gap_eur) : "-"}</td>
                    <td className="hidden py-2 text-right text-xs tabular-nums text-slate-600 sm:table-cell">
                      {formatRate(line.stock_xirr_pct, 1, true)} / {formatRate(line.benchmark_xirr_pct, 1, true)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
