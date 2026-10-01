import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { DiversityScannerResponse, UnderlyingCompany } from "@/types/diversity"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts"
import { 
  ShieldCheck, 
  AlertTriangle, 
  Info, 
  Globe, 
  Briefcase, 
  Layers, 
  Building
} from "lucide-react"
import { toast } from "sonner"

export function DiversityScanner() {
  const [data, setData] = useState<DiversityScannerResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<"stocks" | "wealth">("stocks")

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await api.get<DiversityScannerResponse>("/analytics/diversity-scanner")
      setData(res)
    } catch (err) {
      toast.error("Erreur lors de l'analyse de la diversité")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(val)
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm space-y-3">
        <div className="h-6 w-6 rounded-full border-2 border-slate-300 border-t-slate-900 animate-spin" />
        <p className="text-xs text-muted-foreground">Analyse de la diversification de vos actifs...</p>
      </div>
    )
  }

  if (!data || data.totals.holdings_count === 0) {
    return (
      <Card className="shadow-sm border-dashed">
        <CardContent className="p-8 text-center space-y-3">
          <div className="h-10 w-10 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center mx-auto">
            <Layers className="h-5 w-5" />
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="font-bold text-sm">Scanner de Diversité & Transparence ETF</h3>
            <p className="text-xs text-muted-foreground">
              Pour décomposer vos ETFs et analyser votre exposition réelle consolidée, commencez par définir votre <strong>Point Zéro</strong> sur l'un de vos comptes d'investissement.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const isWealth = viewMode === "wealth"

  // Data for Top 10 chart
  const topCompaniesChartData = data.top_underlying_companies.slice(0, 10).map((c) => ({
    name: c.name,
    direct: c.direct_value_eur,
    indirect: c.indirect_value_eur,
    total: c.total_value_eur,
    pct: isWealth ? c.pct_total_wealth : c.pct_stocks,
    company: c,
  }))

  const getScoreBadge = (score: number) => {
    if (score >= 80) return <Badge className="bg-emerald-600/90 text-white border-0 text-[10px]">Excellente</Badge>
    if (score >= 60) return <Badge className="bg-slate-700 text-slate-100 border-0 text-[10px]">Bonne</Badge>
    if (score >= 40) return <Badge className="bg-amber-600/90 text-white border-0 text-[10px]">Modérée</Badge>
    return <Badge className="bg-rose-600/90 text-white border-0 text-[10px]">Concentration critique</Badge>
  }

  return (
    <div className="space-y-6">
      {/* 1. Score & Summary Card */}
      <Card className="bg-slate-900 text-white shadow-md border-slate-800 overflow-hidden relative">
        <CardContent className="p-6 md:p-8 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Layers className="h-5 w-5 text-slate-300" />
                <h2 className="text-xl md:text-2xl font-bold tracking-tight">Scanner de Diversité & Transparence ETF</h2>
              </div>
              <p className="text-xs md:text-sm text-slate-400">
                Décomposition des sous-jacents, détection des doublons et cotations de marché en temps réel.
              </p>
            </div>

            {/* Dual View Toggle */}
            <div className="flex items-center bg-slate-800 p-1 rounded-lg border border-slate-700/60 self-start md:self-center">
              <button
                type="button"
                onClick={() => setViewMode("stocks")}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  viewMode === "stocks"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Portefeuille Bourse Seul
              </button>
              <button
                type="button"
                onClick={() => setViewMode("wealth")}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  viewMode === "wealth"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Patrimoine Global ("À côté")
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <span className="text-xs text-slate-400">Score de Diversité Numera</span>
              <div className="flex items-center gap-2">
                <span className="text-3xl font-extrabold">{data.score}/100</span>
                {getScoreBadge(data.score)}
              </div>
              <p className="text-[11px] text-slate-400">{data.score_label}</p>
            </div>

            <div className="space-y-1">
              <span className="text-xs text-slate-400">Portefeuille Bourse</span>
              <div className="text-2xl font-bold font-mono amount-blur">
                {formatCurrency(data.totals.stocks_eur)}
              </div>
              <p className="text-[11px] text-slate-400">
                {data.totals.holdings_count} position{data.totals.holdings_count > 1 ? "s" : ""} ({data.totals.etfs_count} ETF{data.totals.etfs_count > 1 ? "s" : ""})
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-xs text-slate-400">Épargne sécurisée & Liquidités</span>
              <div className="text-2xl font-bold font-mono amount-blur">
                {formatCurrency(data.totals.epargne_eur + data.totals.fonds_euros_eur + data.totals.courant_eur)}
              </div>
              <p className="text-[11px] text-slate-400">Livrets, Fonds Euros, Comptes courants</p>
            </div>

            <div className="space-y-1">
              <span className="text-xs text-slate-400">Patrimoine Net Total</span>
              <div className="text-2xl font-bold font-mono amount-blur text-white">
                {formatCurrency(data.totals.wealth_eur)}
              </div>
              <p className="text-[11px] text-slate-400">Bourse + Épargne + Liquidités</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. Alerts & Overlaps Section */}
      {data.alerts.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-slate-500" />
              Diagnostics & Alertes de Surexposition ({data.alerts.length})
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.alerts.map((alert, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-start gap-3 shadow-sm transition-all"
              >
                <div className="shrink-0 mt-0.5">
                  {alert.type === "danger" ? (
                    <AlertTriangle className="h-4 w-4 text-rose-600" />
                  ) : alert.type === "warning" ? (
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                  ) : (
                    <Info className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                  )}
                </div>
                <div className="space-y-1">
                  <h4 className="font-semibold text-xs text-slate-900 dark:text-slate-100">{alert.title}</h4>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">{alert.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Look-Through Top Companies Consolidated */}
      <Card className="shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-2 border-b">
          <div>
            <div className="flex items-center gap-2">
              <Building className="h-4 w-4 text-slate-500" />
              <CardTitle className="text-base font-bold">
                Top 10 Entreprises Détenues Réellement (Look-Through)
              </CardTitle>
            </div>
            <CardDescription className="text-xs mt-0.5">
              Exposition consolidée : fraction détenue en direct + fractions sous-jacentes de vos ETFs.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-3 text-xs text-muted-foreground mr-2">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-slate-900 dark:bg-slate-100" /> Direct
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-slate-400 dark:bg-slate-600" /> Via ETFs
              </span>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-6">
          <div className="h-[340px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={topCompaniesChartData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
              >
                <XAxis
                  type="number"
                  tickFormatter={(v) => `${v.toFixed(0)}€`}
                  tick={{ fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 11, fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  width={110}
                />
                <Tooltip
                  formatter={(val: number, name: string) => [
                    formatCurrency(val),
                    name === "direct" ? "Détenu en direct" : "Détenu via ETFs",
                  ]}
                  labelFormatter={(label) => `Actif : ${label}`}
                  contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }}
                />
                <Bar dataKey="direct" stackId="a" fill="#0f172a" />
                <Bar dataKey="indirect" stackId="a" fill="#94a3b8" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* List breakdown of top companies */}
          <div className="mt-6 border-t pt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.top_underlying_companies.slice(0, 8).map((comp, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between"
              >
                <div className="flex flex-col min-w-0 pr-2">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-xs truncate">{comp.name}</span>
                    {comp.has_overlap && (
                      <Badge variant="outline" className="text-[9px] px-1.5 py-0 font-normal border-slate-300 dark:border-slate-700">
                        Doublon ({comp.sources.length} sources)
                      </Badge>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground truncate">
                    {comp.sources.map((s) => `${s.source} (${s.pct_in_source}%)`).join(" + ")}
                  </span>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-xs font-bold font-mono">
                    {isWealth ? `${comp.pct_total_wealth}%` : `${comp.pct_stocks}%`}
                  </span>
                  <div className="text-[10px] text-muted-foreground amount-blur font-mono">
                    {formatCurrency(comp.total_value_eur)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 4. Geography and Sectors Real Look-Through */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Real Geography */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2 border-b">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-slate-500" />
              <CardTitle className="text-base font-bold">Répartition Géographique Réelle</CardTitle>
            </div>
            <CardDescription className="text-xs">
              Les ETFs ont été décomposés pays par pays (au lieu de rester en catégorie "Monde").
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            {data.countries.slice(0, 6).map((c, i) => {
              const pct = isWealth ? c.percentage_total_wealth : c.percentage_stocks
              return (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium">{c.name}</span>
                    <span className="font-bold font-mono">{pct.toFixed(1)}% ({formatCurrency(c.value_eur)})</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-slate-800 dark:bg-slate-200 rounded-full transition-all"
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Real Sectors */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2 border-b">
            <div className="flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-slate-500" />
              <CardTitle className="text-base font-bold">Répartition Sectorielle Réelle</CardTitle>
            </div>
            <CardDescription className="text-xs">
              Pondération économique consolidée par secteur d'activité.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            {data.sectors.slice(0, 6).map((s, i) => {
              const pct = isWealth ? s.percentage_total_wealth : s.percentage_stocks
              return (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium">{s.name}</span>
                    <span className="font-bold font-mono">{pct.toFixed(1)}% ({formatCurrency(s.value_eur)})</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-slate-600 dark:bg-slate-400 rounded-full transition-all"
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
