import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { 
  TrendingUp, 
  Wallet,
  Activity,
  Globe,
  Layers,
  Briefcase,
  Building,
  AlertTriangle,
  Info,
  ShieldCheck,
  ChevronDown,
  ChevronUp
} from "lucide-react"
import { api } from "@/lib/api"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import WorldMap from "@/components/ui/WorldMap"
import { AllocationTreemap } from "@/components/analytics/AllocationTreemap"
import { DiversityScannerResponse, UnderlyingCompany } from "@/types/diversity"

const COLORS = ["#0f172a", "#334155", "#64748b", "#94a3b8", "#cbd5e1", "#e2e8f0", "#f8fafc"]

export default function Investments() {
  const navigate = useNavigate()
  const [allocation, setAllocation] = useState<any>(null)
  const [advancedAllocation, setAdvancedAllocation] = useState<any>(null)
  const [diversity, setDiversity] = useState<DiversityScannerResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [drillDown, setDrillDown] = useState<{ title: string, items: any[] } | null>(null)
  const [viewMode, setViewMode] = useState<"stocks" | "wealth">("stocks")
  const [showAlerts, setShowAlerts] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const [basic, advanced, divResp] = await Promise.all([
          api.get("/analytics/investments-allocation"),
          api.get("/analytics/investments-allocation-advanced"),
          api.get<DiversityScannerResponse>("/analytics/diversity-scanner").catch(() => null)
        ])
        setAllocation(basic)
        setAdvancedAllocation(advanced)
        setDiversity(divResp)
      } catch (error) {
        toast.error("Erreur lors du chargement des investissements")
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value)
  }

  const handleAccountClick = (accountId: number) => {
    navigate(`/accounts/${accountId}`)
  }

  const getDrilldownItems = (clickedData: any) => {
    if (!clickedData) return []
    if (Array.isArray(clickedData.items)) return clickedData.items
    if (clickedData.payload && Array.isArray(clickedData.payload.items)) return clickedData.payload.items
    if (clickedData.payload?.payload && Array.isArray(clickedData.payload.payload.items)) return clickedData.payload.payload.items
    return []
  }

  const getDrilldownTitle = (prefix: string, clickedData: any) => {
    if (!clickedData) return prefix
    const name = clickedData.name || clickedData.payload?.name || clickedData.payload?.payload?.name || ""
    return `${prefix} : ${name}`
  }

  if (loading) return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-10 w-10 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        <p className="text-slate-500 font-medium text-sm">Chargement de vos investissements et analyse Look-Through...</p>
      </div>
    </div>
  )

  const isWealth = viewMode === "wealth"

  // Chart data for accounts
  const chartData = (allocation?.items || []).map((item: any) => ({
    name: item.account_name,
    value: item.current_value,
    percentage: item.percentage,
    id: item.account_id
  }))

  // Real Look-Through Countries for WorldMap
  const worldMapData = (diversity?.countries && diversity.countries.length > 0)
    ? diversity.countries.map((c) => ({
        name: c.name,
        value: c.value_eur,
        percentage: isWealth ? c.percentage_total_wealth : c.percentage_stocks
      }))
    : (advancedAllocation?.by_geographic_zone || [])

  // Real Look-Through Sectors for Sector PieChart
  const sectorData = (diversity?.sectors && diversity.sectors.length > 0)
    ? diversity.sectors.map((s) => ({
        name: s.name,
        value: s.value_eur,
        percentage: isWealth ? s.percentage_total_wealth : s.percentage_stocks,
        items: []
      }))
    : (advancedAllocation?.by_sector || [])

  // Top 10 underlying companies (Look-Through)
  const topCompaniesChartData = (diversity?.top_underlying_companies || []).slice(0, 10).map((c) => ({
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
    return <Badge className="bg-rose-600/90 text-white border-0 text-[10px]">Concentration</Badge>
  }

  const totalValueDisplay = isWealth
    ? (diversity?.totals?.wealth_eur || allocation?.total_current_value || 0)
    : (allocation?.total_current_value || diversity?.totals?.stocks_eur || 0)

  return (
    <div className="space-y-8">
      {/* Header & Global Dual-View Toggle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Investissements</h1>
          <p className="text-muted-foreground text-xs md:text-sm mt-0.5">
            Performance, répartition et transparence Look-Through de votre portefeuille.
          </p>
        </div>

        {/* Dual-View Switch ("Portefeuille Bourse Seul" vs "Patrimoine Global / À côté") */}
        {diversity && diversity.totals.wealth_eur > diversity.totals.stocks_eur && (
          <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700 self-start md:self-center">
            <button
              type="button"
              onClick={() => setViewMode("stocks")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                !isWealth
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
              }`}
            >
              Portefeuille Bourse Seul
            </button>
            <button
              type="button"
              onClick={() => setViewMode("wealth")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                isWealth
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
              }`}
            >
              Patrimoine Global ("À côté")
            </button>
          </div>
        )}
      </div>

      {/* KPI Section (Consolidated 4-Cards Grid) */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-slate-900 text-white shadow-md border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
            <CardTitle className="text-xs font-medium text-slate-300">
              {isWealth ? "Patrimoine Net Total" : "Valeur Portefeuille Bourse"}
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              <span className="amount-blur">{formatCurrency(totalValueDisplay)}</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              {isWealth ? "Bourse + Livrets + Fonds Euros + Cash" : "Somme des valorisations connues"}
            </p>
          </CardContent>
        </Card>
        
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
            <CardTitle className="text-xs font-medium">Performance Globale</CardTitle>
            <Activity className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold font-mono ${allocation?.total_gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              <span className="amount-blur">
                {allocation?.total_gain_eur >= 0 ? "+" : ""}{formatCurrency(allocation?.total_gain_eur || 0)}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              {(allocation?.total_performance_pct || 0).toFixed(2)}% de rendement total
            </p>
          </CardContent>
        </Card>

        {diversity ? (
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
              <CardTitle className="text-xs font-medium">Score de Diversité</CardTitle>
              <ShieldCheck className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold font-mono">{diversity.score}/100</span>
                {getScoreBadge(diversity.score)}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1 truncate">
                {diversity.score_label}
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
              <CardTitle className="text-xs font-medium">Épargne sécurisée</CardTitle>
              <Wallet className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">
                <span className="amount-blur">
                  {formatCurrency((diversity?.totals?.epargne_eur || 0) + (diversity?.totals?.fonds_euros_eur || 0))}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">Livrets & Fonds Euros</p>
            </CardContent>
          </Card>
        )}

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
            <CardTitle className="text-xs font-medium">Supports & Lignes</CardTitle>
            <Wallet className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {allocation?.items?.length || 0} <span className="text-xs font-normal text-muted-foreground">comptes</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              {diversity?.totals?.holdings_count || 0} position{(diversity?.totals?.holdings_count || 0) > 1 ? "s" : ""}
              {diversity?.totals?.etfs_count ? ` (${diversity.totals.etfs_count} ETF${diversity.totals.etfs_count > 1 ? "s" : ""})` : ""}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Diagnostics & Overexposure Alerts (If any) */}
      {diversity && diversity.alerts && diversity.alerts.length > 0 && (
        <Card className="shadow-sm border-slate-200 dark:border-slate-800">
          <CardHeader 
            className="py-3 px-4 flex flex-row items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors"
            onClick={() => setShowAlerts(!showAlerts)}
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-slate-600 dark:text-slate-400" />
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Diagnostics de Diversité & Alertes de Surexposition ({diversity.alerts.length})
              </CardTitle>
            </div>
            <div className="text-muted-foreground">
              {showAlerts ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </CardHeader>
          {showAlerts && (
            <CardContent className="pt-0 pb-4 px-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t">
                {diversity.alerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-start gap-2.5"
                  >
                    <div className="shrink-0 mt-0.5">
                      {alert.type === "danger" ? (
                        <AlertTriangle className="h-4 w-4 text-rose-600" />
                      ) : alert.type === "warning" ? (
                        <AlertTriangle className="h-4 w-4 text-amber-600" />
                      ) : (
                        <Info className="h-4 w-4 text-slate-500" />
                      )}
                    </div>
                    <div className="space-y-0.5 min-w-0">
                      <h4 className="font-semibold text-xs text-slate-900 dark:text-slate-100 truncate">{alert.title}</h4>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">{alert.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* Section 1: Répartition par comptes */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Répartition par compte</h2>
          <p className="text-xs md:text-sm text-muted-foreground">Vos investissements séparés par enveloppe fiscale.</p>
        </div>
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-7">
          <Card className="lg:col-span-4 shadow-sm">
            <CardContent className="h-[340px] p-4">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={window.innerWidth < 640 ? 60 : 90}
                    outerRadius={window.innerWidth < 640 ? 100 : 130}
                    paddingAngle={5}
                    dataKey="value"
                    nameKey="name"
                    onClick={(data) => handleAccountClick(data.id)}
                    className="cursor-pointer outline-none"
                  >
                    {chartData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number, name: string) => [formatCurrency(value), name]}
                    contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card className="lg:col-span-3 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-bold">Détails de l'allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {allocation?.items.map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex flex-col gap-1 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-2 -mx-2 rounded-lg transition-colors group"
                    onClick={() => handleAccountClick(item.account_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                        <span className="font-medium text-xs sm:text-sm truncate max-w-[150px] sm:max-w-none group-hover:text-slate-600 transition-colors">
                          {item.account_name} 
                          {item.currency && item.currency !== "EUR" && (
                            <span className="text-xs text-muted-foreground ml-1">({item.currency})</span>
                          )}
                        </span>
                      </div>
                      <span className="font-bold text-xs sm:text-sm shrink-0 font-mono">{item.percentage.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground ml-5 font-mono">
                      <span className="amount-blur">{formatCurrency(item.current_value)}</span>
                      <span className={`amount-blur ${item.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                        {item.gain_eur >= 0 ? "+" : ""}{formatCurrency(item.gain_eur)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Section 2: Transparence Look-Through & Analyses Avancées */}
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Transparence Look-Through & Analyses Avancées</h2>
          <p className="text-xs md:text-sm text-muted-foreground">
            Exposition consolidée : fraction détenue en direct + fractions sous-jacentes de vos ETFs décomposés.
          </p>
        </div>

        {/* 2.1 Top 10 Entreprises Détenues Réellement */}
        {topCompaniesChartData.length > 0 && (
          <Card className="shadow-sm">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <Building className="h-4 w-4 text-slate-500" />
                  <CardTitle className="text-base font-bold">
                    Top 10 Entreprises Détenues Réellement (Look-Through)
                  </CardTitle>
                </div>
                <CardDescription className="text-xs mt-0.5">
                  Détail par entreprise en agrégeant vos actions directes et vos parts d'ETFs.
                </CardDescription>
              </div>

              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-slate-900 dark:bg-slate-100" /> Direct
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-slate-400 dark:bg-slate-600" /> Via ETFs
                </span>
              </div>
            </CardHeader>

            <CardContent className="pt-6">
              <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={topCompaniesChartData}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 70, bottom: 5 }}
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
                      width={100}
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

              {/* Underlying companies detail cards with full source breakdown */}
              <div className="mt-4 border-t pt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                {(diversity?.top_underlying_companies || []).slice(0, 8).map((comp, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between transition-colors"
                  >
                    <div className="flex flex-col min-w-0 pr-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-semibold text-xs truncate">{comp.name}</span>
                        {comp.has_overlap && (
                          <Badge variant="outline" className="text-[9px] px-1.5 py-0 font-normal border-slate-300 dark:border-slate-700">
                            Doublon ({comp.sources.length} sources)
                          </Badge>
                        )}
                      </div>
                      <span className="text-[11px] text-muted-foreground truncate mt-0.5">
                        {comp.sources.map((s) => `${s.source} (${s.pct_in_source}%)`).join(" + ")}
                      </span>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="text-xs font-bold font-mono">
                        {isWealth ? `${comp.pct_total_wealth}%` : `${comp.pct_stocks}%`}
                      </div>
                      <div className="text-[10px] text-muted-foreground font-mono amount-blur mt-0.5">
                        {formatCurrency(comp.total_value_eur)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 2.2 Treemap & Sectors / Asset Class */}
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-b">
            <div>
              <CardTitle className="text-base font-bold">Vue d'ensemble de l'allocation (Treemap)</CardTitle>
            </div>
            <Badge variant="secondary" className="bg-slate-100 text-slate-900 pointer-events-none shadow-none border-none">
              Treemap
            </Badge>
          </CardHeader>
          <CardContent className="pt-6">
            {advancedAllocation ? (
              <AllocationTreemap 
                data={advancedAllocation.by_asset_class} 
                onItemClick={(node) => setDrillDown({ title: getDrilldownTitle("Classe d'actif", node), items: getDrilldownItems(node) })}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center">
                <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* 2.3 Double Donut : Par Classe d'actif & Par Secteur Réel */}
        <div className="grid gap-6 grid-cols-1 md:grid-cols-2">
          {/* Classe d'actif */}
          <Card className="shadow-sm">
            <CardHeader className="border-b pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-slate-500" />
                <CardTitle className="text-base font-bold">Par Classe d'actif</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="h-[280px] flex flex-col items-center pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={advancedAllocation?.by_asset_class || []}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={5}
                    dataKey="value"
                    nameKey="name"
                    onClick={(data) => setDrillDown({ title: getDrilldownTitle("Classe d'actif", data), items: getDrilldownItems(data) })}
                    className="cursor-pointer outline-none"
                  >
                    {(advancedAllocation?.by_asset_class || []).map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                </PieChart>
              </ResponsiveContainer>
              <div className="w-full space-y-1 mt-4 px-2">
                {(advancedAllocation?.by_asset_class || []).slice(0, 3).map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex items-center justify-between text-xs cursor-pointer hover:text-slate-600 transition-colors"
                    onClick={() => setDrillDown({ title: `Classe d'actif : ${item.name}`, items: item.items || [] })}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="truncate max-w-[150px]">{item.name}</span>
                    </div>
                    <span className="font-bold font-mono">{item.percentage}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Secteur Économique Look-Through */}
          <Card className="shadow-sm">
            <CardHeader className="border-b pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-slate-500" />
                  <CardTitle className="text-base font-bold">Par Secteur (Look-Through Réel)</CardTitle>
                </div>
                {diversity?.sectors && diversity.sectors.length > 0 && (
                  <Badge variant="outline" className="text-[10px] text-muted-foreground font-normal">
                    ETFs décomposés
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="h-[280px] flex flex-col items-center pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sectorData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={5}
                    dataKey="value"
                    nameKey="name"
                    className="outline-none"
                  >
                    {sectorData.map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                </PieChart>
              </ResponsiveContainer>
              <div className="w-full space-y-1 mt-4 px-2">
                {sectorData.slice(0, 4).map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="truncate max-w-[150px]">{item.name}</span>
                    </div>
                    <span className="font-bold font-mono">{item.percentage.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 2.4 Carte Mondiale Interactive avec Vraies Données Look-Through */}
        <Card className="shadow-sm overflow-hidden">
          <CardHeader className="border-b bg-slate-50/50 dark:bg-slate-800/30 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-slate-500" />
                <CardTitle className="text-base font-bold">Répartition Géographique Mondiale Réelle</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                {diversity?.countries && diversity.countries.length > 0 && (
                  <Badge variant="outline" className="text-[10px] text-muted-foreground font-normal">
                    Look-Through actif
                  </Badge>
                )}
                <Badge variant="outline" className="bg-white dark:bg-slate-900 text-[10px]">
                  Interactif
                </Badge>
              </div>
            </div>
            <CardDescription className="text-xs">
              Les pays sont décomposés à partir des sous-jacents de vos ETFs et de vos actions en direct.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0 relative bg-slate-50/30">
            <div className="h-[420px] w-full relative">
              <div className="absolute top-4 left-4 z-10 text-[11px] text-slate-500 bg-white/90 dark:bg-slate-900/90 backdrop-blur shadow-sm px-3 py-1.5 rounded-md border border-slate-200 dark:border-slate-800">
                Molette pour zoomer • Cliquer-glisser pour déplacer
              </div>
              <WorldMap data={worldMapData} />
            </div>

            {/* Top 5 Countries Summary List below the Map */}
            {worldMapData.length > 0 && (
              <div className="border-t border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900">
                <div className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
                  Principaux pays d'exposition
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  {worldMapData.slice(0, 5).map((c: any, i: number) => (
                    <div key={i} className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold truncate">{c.name}</span>
                        <span className="font-bold font-mono">{c.percentage.toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-slate-900 dark:bg-slate-100 rounded-full transition-all"
                          style={{ width: `${Math.min(100, c.percentage)}%` }}
                        />
                      </div>
                      <div className="text-[10px] text-muted-foreground font-mono">
                        {formatCurrency(c.value)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Section 3: Performance détaillée des comptes */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Performance détaillée des comptes</h2>
          <p className="text-xs md:text-sm text-muted-foreground">Valorisation par support d'investissement.</p>
        </div>
        <Card className="shadow-sm">
          <CardContent className="h-[280px] px-2 sm:px-6 pt-6">
             <ResponsiveContainer width="100%" height="100%">
               <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                 <XAxis 
                   dataKey="name" 
                   axisLine={false} 
                   tickLine={false} 
                   tick={{ fontSize: 10 }}
                   interval={0}
                   angle={-45}
                   textAnchor="end"
                   height={60}
                 />
                 <YAxis 
                   axisLine={false} 
                   tickLine={false} 
                   tick={{ fontSize: 10 }}
                   tickFormatter={(v) => `${v}€`} 
                 />
                 <Tooltip 
                    formatter={(value: number, name: string) => [formatCurrency(value), name]}
                    contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }}
                 />
                 <Bar 
                   dataKey="value" 
                   fill="#0f172a" 
                   radius={[4, 4, 0, 0]} 
                   onClick={(data) => handleAccountClick(data.id)}
                   className="cursor-pointer hover:opacity-80 transition-opacity"
                 />
               </BarChart>
             </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Drilldown Dialog */}
      <Dialog open={!!drillDown} onOpenChange={(open) => !open && setDrillDown(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{drillDown?.title}</DialogTitle>
            <DialogDescription>
              Détail des comptes contribuant à cette catégorie.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 space-y-3">
            {(drillDown?.items || []).map((item: any, i: number) => (
              <div 
                key={i} 
                className="flex items-center justify-between p-3 rounded-lg border bg-slate-50/50 cursor-pointer hover:bg-slate-50 transition-colors group"
                onClick={() => {
                  setDrillDown(null)
                  handleAccountClick(item.account_id)
                }}
              >
                <div className="flex flex-col">
                  <span className="font-medium text-xs sm:text-sm group-hover:text-slate-600 transition-colors">
                    {item.account_name || "Compte sans nom"}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    {typeof item.percentage_of_group === 'number' ? `${item.percentage_of_group.toFixed(1)}%` : `${item.percentage_of_group || 0}%`} du groupe
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-xs sm:text-sm font-mono amount-blur">{formatCurrency(item.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

