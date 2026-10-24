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
  RefreshCw
} from "lucide-react"
import { Button } from "@/components/ui/button"
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
import { CompositionField, CompositionSource, DiversityScannerResponse } from "@/types/diversity"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { useIsMobile } from "@/hooks/useIsMobile"
import { formatAmountWithShare, formatCurrency, formatRate } from "@/lib/utils"

const COMPOSITION_FIELDS: { key: CompositionField; label: string }[] = [
  { key: "sectors", label: "Secteurs" },
  { key: "top_holdings", label: "Top 10" },
  { key: "countries", label: "Pays" },
]

const SOURCE_LABELS: Record<CompositionSource, { label: string; className: string }> = {
  yahoo: { label: "Yahoo", className: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-900" },
  preset: { label: "Préréglage", className: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-900" },
  manual: { label: "Saisie", className: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700" },
}

const COLORS = ["#000000", "#4b5563", "#9ca3af", "#d1d5db", "#e5e7eb", "#f3f4f6", "#f8fafc"]

export default function Investments() {
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [allocation, setAllocation] = useState<any>(null)
  const [advancedAllocation, setAdvancedAllocation] = useState<any>(null)
  const [diversity, setDiversity] = useState<DiversityScannerResponse | null>(null)
const [loading, setLoading] = useState(true)
  const [drillDown, setDrillDown] = useState<{ title: string, items: any[] } | null>(null)
  const [refreshingCompositions, setRefreshingCompositions] = useState(false)

  const refreshCompositions = async () => {
    setRefreshingCompositions(true)
    try {
      const res = await api.post<{ refreshed: number }>("/etf-profiles/refresh-held", {})
      const div = await api.get<DiversityScannerResponse>("/analytics/diversity-scanner")
      if (div && div.totals.holdings_count > 0) setDiversity(div)
      toast.success(`${res.refreshed} composition${res.refreshed > 1 ? "s" : ""} actualisée${res.refreshed > 1 ? "s" : ""} depuis Yahoo`)
    } catch {
      toast.error("Impossible d'actualiser les compositions")
    } finally {
      setRefreshingCompositions(false)
    }
  }

  useEffect(() => {
    async function loadData() {
      try {
        const [basic, advanced] = await Promise.all([
          api.get("/analytics/investments-allocation"),
          api.get("/analytics/investments-allocation-advanced")
        ])
        setAllocation(basic)
        setAdvancedAllocation(advanced)
        // Load diversity data separately (non-blocking, may have no holdings)
        try {
          const div = await api.get<DiversityScannerResponse>("/analytics/diversity-scanner")
          if (div && div.totals.holdings_count > 0) setDiversity(div)
        } catch { /* No holdings yet, that's fine */ }
      } catch (error) {
        toast.error("Erreur lors du chargement de l'allocation")
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

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
        <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        <p className="text-slate-500 font-medium">Chargement de vos investissements...</p>
      </div>
    </div>
  )

  const chartData = (allocation?.items || []).map((item: any) => ({
    name: item.account_name,
    value: item.current_value,
    percentage: item.percentage,
    id: item.account_id
  }))

  return (
    <div className="space-y-8 md:space-y-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Investissements</h1>
        <p className="text-sm text-muted-foreground mt-1 md:text-base">Suivez la performance et la répartition de votre patrimoine investi.</p>
      </div>

      {/* KPI Section */}
      <div className={`grid gap-3 grid-cols-2 md:gap-4 ${diversity ? "md:grid-cols-4" : "md:grid-cols-3"}`}>
        <Card className="col-span-2 bg-slate-900 text-white shadow-md border-slate-800 md:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Valeur Totale</CardTitle>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tabular-nums">
              <span className="amount-blur">{formatCurrency(allocation?.total_current_value || 0)}</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">Positions × cours (comptes titres) et derniers relevés (assurance-vie)</p>
          </CardContent>
        </Card>
        
        <Card className="col-span-2 shadow-sm md:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performance Globale</CardTitle>
            <Activity className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold tabular-nums md:text-3xl ${allocation?.total_gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              <span className="amount-blur">
                {allocation?.total_gain_eur >= 0 ? "+" : ""}{formatCurrency(allocation?.total_gain_eur || 0)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {formatRate(allocation?.total_performance_pct || 0)} de rendement total
            </p>
          </CardContent>
        </Card>

        <Card className={`shadow-sm ${diversity ? "" : "col-span-2 md:col-span-1"}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Supports</CardTitle>
            <Wallet className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold md:text-3xl">{allocation?.items.length || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Comptes d'investissement</p>
          </CardContent>
        </Card>

        {diversity && (
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Score de Diversité</CardTitle>
              <ShieldCheck className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold md:text-3xl">{diversity.score}</span>
                <span className="text-sm text-muted-foreground">/100</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{diversity.score_label}</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Alertes de surexposition (discret) */}
      {diversity && diversity.alerts.length > 0 && (
        <details className="group text-xs text-muted-foreground">
          <summary className="flex min-h-11 w-fit cursor-pointer select-none items-center gap-1.5 hover:text-foreground md:min-h-0">
            <AlertTriangle className="h-3 w-3" />
            {diversity.alerts.length} alerte{diversity.alerts.length > 1 ? "s" : ""} de surexposition
          </summary>
          <ul className="mt-2 space-y-1 pl-4.5 border-l ml-1.5 pl-3">
            {diversity.alerts.map((alert, idx) => (
              <li key={idx}>
                <span className="font-medium text-foreground/80">{alert.title}</span> · {alert.message}
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Section 1: Répartition par comptes */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Répartition par compte</h2>
          <p className="text-sm text-muted-foreground">Vos investissements séparés par enveloppe.</p>
        </div>
        <Card className="shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="flex flex-col items-start justify-between gap-2 border-b bg-slate-50/50 pb-4 sm:flex-row sm:items-center">
            <CardTitle className="text-base font-bold">Détails de l'allocation</CardTitle>
            <span className="text-sm font-semibold text-slate-500 bg-slate-100/80 px-3 py-1 rounded-lg">
              Total : <span className="amount-blur text-slate-900 font-bold">{formatCurrency(allocation?.total_current_value || 0)}</span>
            </span>
          </CardHeader>
          <CardContent className="p-4 md:p-6">
            <div className="grid grid-cols-1 items-center gap-6 md:gap-8 lg:grid-cols-12">
              {/* Donut Chart */}
              <div className="min-w-0 lg:col-span-5 h-[240px] md:h-[300px] flex items-center justify-center relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={75}
                      outerRadius={105}
                      paddingAngle={3}
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
                      formatter={(value: number, name: string) => [formatAmountWithShare(value, chartData.reduce((s: number, i: any) => s + (i.value || 0), 0)), name]}
                      contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Center Text (Total) */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total</span>
                  <span className="text-lg font-bold text-slate-800 amount-blur">
                    {formatCurrency(allocation?.total_current_value || 0)}
                  </span>
                  <span className="text-[11px] text-muted-foreground font-medium">
                    {allocation?.items?.length || 0} {allocation?.items?.length > 1 ? "comptes" : "compte"}
                  </span>
                </div>
              </div>

              {/* Détails de l'allocation */}
              <div className="min-w-0 lg:col-span-7 space-y-2.5 md:max-h-[300px] md:overflow-y-auto md:pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                {allocation?.items?.map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex min-h-11 flex-col gap-1 cursor-pointer hover:bg-slate-50/80 p-3 md:p-2.5 rounded-xl border border-slate-100 hover:border-slate-200 transition-all group"
                    onClick={() => handleAccountClick(item.account_id)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2.5">
                        <div 
                          className="h-3 w-3 rounded-full shrink-0" 
                          style={{ backgroundColor: COLORS[i % COLORS.length] }} 
                        />
                        <span className="font-semibold text-sm truncate min-w-0 text-slate-800 group-hover:text-slate-900 transition-colors">
                          {item.account_name} 
                          {item.currency && item.currency !== "EUR" && (
                            <span className="text-xs text-muted-foreground ml-1.5 font-normal">({item.currency})</span>
                          )}
                        </span>
                      </div>
                      <span className="font-bold text-sm text-slate-700 shrink-0 tabular-nums">{item.percentage?.toFixed(1) || 0}%</span>
                    </div>
                    <div className="flex flex-wrap justify-between gap-x-2 text-xs text-muted-foreground pl-5.5">
                      <span className="amount-blur font-medium whitespace-nowrap">{formatCurrency(item.current_value)}</span>
                      {item.gain_eur == null ? (
                        <span className="font-medium whitespace-nowrap text-amber-600" title="Aucune valorisation postérieure aux derniers flux de la période">
                          Valeur à actualiser
                        </span>
                      ) : (
                        <span className={`amount-blur font-medium whitespace-nowrap ${item.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                          {item.gain_eur >= 0 ? "+" : ""}{formatCurrency(item.gain_eur)}
                          {item.performance_pct != null && ` (${formatRate(item.performance_pct, 2, true)})`}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Section 2: Performance détaillée */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Performance détaillée</h2>
          <p className="text-sm text-muted-foreground">Historique et évolution de vos supports.</p>
        </div>
        <Card className="shadow-sm">
          <CardContent className="h-[260px] px-2 sm:px-6 pt-6 md:h-[300px]">
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
                   height={isMobile ? 70 : 60}
                   tickFormatter={(v: string) => (isMobile && v.length > 12 ? `${v.slice(0, 11)}…` : v)}
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
                   fill="#000000" 
                   radius={[4, 4, 0, 0]} 
                   onClick={(data) => handleAccountClick(data.id)}
                   className="cursor-pointer hover:opacity-80 transition-opacity"
                 />
               </BarChart>
             </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Section 3: Analyses avancées */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Analyses avancées</h2>
          <p className="text-sm text-muted-foreground">Vision globale de vos actifs sous-jacents (tous comptes confondus).</p>
        </div>
        
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2 border-b">
            <div>
              <CardTitle className="text-base font-bold">Vue d'ensemble de l'allocation</CardTitle>
            </div>
            <Badge variant="secondary" className="bg-slate-100 text-slate-900 pointer-events-none shadow-none border-none">Treemap</Badge>
          </CardHeader>
          <CardContent className="px-3 pt-4 md:px-6 md:pt-6">
            {advancedAllocation ? (
              <AllocationTreemap 
                data={advancedAllocation.by_asset_class} 
                onItemClick={(node) => setDrillDown({ title: getDrilldownTitle("Classe d'actif", node), items: getDrilldownItems(node) })}
              />
            ) : (
              <div className="h-[400px] flex items-center justify-center">
                <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-4 md:gap-6 grid-cols-1 md:grid-cols-2">
          <Card className="shadow-sm">
            <CardHeader className="border-b pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-slate-500" />
                <CardTitle className="text-base">Par Classe d'actif</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-5 flex flex-col items-center">
              <div className="h-[190px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                    <Pie
                      data={advancedAllocation?.by_asset_class || []}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={4}
                      dataKey="value"
                      nameKey="name"
                      onClick={(data) => setDrillDown({ title: getDrilldownTitle("Classe d'actif", data), items: getDrilldownItems(data) })}
                      className="cursor-pointer outline-none"
                    >
                      {(advancedAllocation?.by_asset_class || []).map((_: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatAmountWithShare(value, (advancedAllocation?.by_asset_class || []).reduce((s: number, i: any) => s + (i.value || 0), 0))} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="w-full space-y-1.5 mt-3 px-2">
                {(advancedAllocation?.by_asset_class || []).slice(0, 4).map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex min-h-9 items-center justify-between gap-2 text-xs cursor-pointer hover:text-slate-600 transition-colors md:min-h-0"
                    onClick={() => setDrillDown({ title: `Classe d'actif : ${item.name}`, items: item.items || [] })}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="truncate max-w-[200px] md:max-w-[150px]">{item.name}</span>
                    </div>
                    <span className="font-bold shrink-0">{item.percentage}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader className="border-b pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-slate-500" />
                  <CardTitle className="text-base">Par Secteur</CardTitle>
                </div>
                {diversity && diversity.sectors.length > 0 && (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-600 text-[10px] pointer-events-none shadow-none border-none">Look-Through</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-5 flex flex-col items-center">
              {(() => {
                const sectorData = diversity && diversity.sectors.length > 0
                  ? diversity.sectors.map(s => ({ name: s.name, value: s.value_eur, percentage: s.percentage_stocks }))
                  : (advancedAllocation?.by_sector || [])
                return (
                  <>
                    <div className="h-[190px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                          <Pie
                            data={sectorData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={75}
                            paddingAngle={4}
                            dataKey="value"
                            nameKey="name"
                            className="outline-none"
                          >
                            {sectorData.map((_: any, index: number) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value: number) => formatAmountWithShare(value, sectorData.reduce((s: number, i: any) => s + (i.value || 0), 0))} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="w-full space-y-1.5 mt-3 px-2">
                      {sectorData.slice(0, 4).map((item: any, i: number) => (
                        <div 
                          key={i} 
                          className="flex items-center justify-between text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                            <span className="truncate max-w-[200px] md:max-w-[150px]">{item.name}</span>
                          </div>
                          <span className="font-bold shrink-0">{typeof item.percentage === 'number' ? item.percentage.toFixed(1) : item.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </>
                )
              })()}
            </CardContent>
          </Card>
        </div>

        {/* Top 10 Companies Look-Through */}
        {diversity && diversity.top_underlying_companies.length > 0 && (
          <Card className="shadow-sm">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <Building className="h-4 w-4 text-slate-500" />
                  <CardTitle className="text-base font-bold">Top 10 Entreprises Détenues (Look-Through)</CardTitle>
                </div>
                <CardDescription className="text-xs mt-0.5">
                  Exposition consolidée : direct + sous-jacents de vos ETFs.
                </CardDescription>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-black" /> Direct
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-slate-400" /> Via ETFs
                </span>
              </div>
            </CardHeader>
            <CardContent className="px-2 pt-4 md:px-6 md:pt-6">
              {(() => {
                const topCompaniesData = diversity.top_underlying_companies.slice(0, 10).map((c) => {
                  const total = c.total_value_eur || (c.direct_value_eur + c.indirect_value_eur)
                  return {
                    name: c.name,
                    ticker: c.ticker,
                    direct: c.direct_value_eur,
                    indirect: c.indirect_value_eur,
                    total: total,
                    pct: c.pct_stocks,
                    sources: c.sources,
                    has_overlap: c.has_overlap,
                  }
                })

                return (
                  <div className="h-[340px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={topCompaniesData}
                        layout="vertical"
                        margin={{ top: 5, right: isMobile ? 8 : 30, left: isMobile ? 0 : 15, bottom: 5 }}
                      >
                        <XAxis
                          type="number"
                          tickFormatter={(v) => `${v.toFixed(0)}€`}
                          tick={{ fontSize: 10 }}
                          tickCount={isMobile ? 3 : 5}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          tick={(tickProps: any) => {
                            const { x, y, payload } = tickProps
                            const comp = topCompaniesData.find((c) => c.name === payload.value)
                            return (
                              <g transform={`translate(${x},${y})`}>
                                <foreignObject x={isMobile ? -105 : -135} y={-10} width={isMobile ? 100 : 130} height={20}>
                                  <div
                                    className="flex items-center justify-end gap-1.5 h-full pr-1 overflow-hidden"
                                    title={payload.value}
                                  >
                                    <CompanyLogo
                                      ticker={comp?.ticker}
                                      name={payload.value}
                                      className="h-4 w-4 rounded-xs shrink-0"
                                    />
                                    <span className="text-[11px] font-medium text-slate-700 truncate max-w-[75px] md:max-w-[105px]">
                                      {payload.value}
                                    </span>
                                  </div>
                                </foreignObject>
                              </g>
                            )
                          }}
                          axisLine={false}
                          tickLine={false}
                          width={isMobile ? 110 : 140}
                        />
                        <Tooltip
                          cursor={false}
                          content={({ active, payload, label }: any) => {
                            if (active && payload && payload.length) {
                              const d = payload[0].payload
                              return (
                                <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-md text-xs space-y-1.5 min-w-[210px]">
                                  <div className="flex items-center justify-between border-b pb-1.5 gap-2">
                                    <div className="flex items-center gap-2.5 min-w-0">
                                      <CompanyLogo
                                        ticker={d.ticker}
                                        name={label || d.name}
                                        className="h-6 w-6 rounded-md shadow-2xs shrink-0"
                                      />
                                      <div className="flex flex-col min-w-0">
                                        <span className="font-bold text-slate-900 truncate">{label || d.name}</span>
                                        {d.ticker && (
                                          <span className="text-[10px] text-slate-400 font-mono font-medium">{d.ticker}</span>
                                        )}
                                      </div>
                                    </div>
                                    {d.has_overlap && (
                                      <Badge variant="outline" className="text-[9px] px-1 py-0 font-normal shrink-0">
                                        Doublon
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="flex justify-between items-center text-slate-900 font-bold">
                                    <span>Apport total :</span>
                                    <span>{formatCurrency(d.total)} ({d.pct.toFixed(1)}%)</span>
                                  </div>
                                  <div className="text-[11px] text-muted-foreground space-y-0.5 pt-1 border-t">
                                    <div className="flex justify-between">
                                      <span className="flex items-center gap-1.5">
                                        <span className="h-2 w-2 rounded-full bg-black shrink-0" /> Détenu en direct :
                                      </span>
                                      <span className="font-medium text-slate-700">{formatCurrency(d.direct)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="flex items-center gap-1.5">
                                        <span className="h-2 w-2 rounded-full bg-slate-400 shrink-0" /> Détenu via ETFs :
                                      </span>
                                      <span className="font-medium text-slate-700">{formatCurrency(d.indirect)}</span>
                                    </div>
                                  </div>
                                </div>
                              )
                            }
                            return null
                          }}
                        />
                        <Bar dataKey="direct" stackId="a" fill="#000000" radius={[0, 0, 0, 0]} />
                        <Bar dataKey="indirect" stackId="a" fill="#9ca3af" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )
              })()}
            </CardContent>
          </Card>
        )}

        <Card className="shadow-sm overflow-hidden">
          <CardHeader className="border-b bg-slate-50/50 pb-3">
            <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 shrink-0 text-slate-500" />
                <CardTitle className="text-base">Répartition géographique mondiale</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                {diversity && diversity.countries.length > 0 && (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-600 text-[10px] pointer-events-none shadow-none border-none">Look-Through</Badge>
                )}
                <Badge variant="outline" className="bg-white">Interactif</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="h-[300px] p-0 relative bg-slate-50/30 md:h-[450px]">
            <div className="absolute top-3 left-3 z-10 rounded-md border bg-white/90 px-2.5 py-1 text-[11px] text-slate-500 shadow-sm backdrop-blur md:top-4 md:left-4 md:px-3 md:py-1.5 md:text-xs">
              <span className="md:hidden">Pincez pour zoomer • Glissez pour déplacer</span><span className="hidden md:inline">Utilisez la molette pour zoomer • Cliquez-glissez pour déplacer</span>
            </div>
            <WorldMap data={
              diversity && diversity.countries.length > 0
                ? diversity.countries.map(c => ({ name: c.name, value: c.value_eur, percentage: c.percentage_stocks }))
                : (advancedAllocation?.by_geographic_zone || [])
            } />
          </CardContent>
        </Card>

        {diversity && diversity.etf_compositions.length > 0 && (
          <Card className="shadow-sm">
            <CardHeader className="border-b pb-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 shrink-0 text-slate-500" />
                  <div>
                    <CardTitle className="text-base">Origine des compositions</CardTitle>
                    <CardDescription className="text-xs">
                      Yahoo fournit secteurs et top 10 (pas les pays) ; à défaut, le préréglage intégré est utilisé. La part non couverte apparaît en « Non renseigné ».
                    </CardDescription>
                  </div>
                </div>
                <Button variant="outline" size="sm" className="h-10 min-w-10 shrink-0 gap-1.5 md:h-9" aria-label="Actualiser" onClick={refreshCompositions} disabled={refreshingCompositions}>
                  <RefreshCw className={`h-3.5 w-3.5 ${refreshingCompositions ? "animate-spin" : ""}`} />
                  <span className="hidden sm:inline">Actualiser</span>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y">
                {diversity.etf_compositions.map((c) => (
                  <div key={c.profile_id} className="flex flex-col gap-2 px-4 py-3 md:px-5 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate">{c.profile_name}</div>
                      <div className="text-xs text-muted-foreground break-words">
                        {c.tickers.join(", ")} · <span className="amount-blur">{formatCurrency(c.value_eur)}</span>
                        {" · "}
                        {c.refreshed_at
                          ? `actualisé le ${new Date(c.refreshed_at + "Z").toLocaleDateString("fr-FR")}`
                          : "jamais actualisé"}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {COMPOSITION_FIELDS.map(({ key, label }) => {
                        const source = c.sources[key]
                        return (
                          <Badge
                            key={key}
                            variant="outline"
                            className={`text-[10px] font-medium shadow-none ${source ? SOURCE_LABELS[source].className : "text-slate-400 border-dashed"}`}
                          >
                            {label} : {source ? SOURCE_LABELS[source].label : "—"}
                          </Badge>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Dialog open={!!drillDown} onOpenChange={(open) => !open && setDrillDown(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{drillDown?.title}</DialogTitle>
            <DialogDescription>
              Détail des comptes contribuant à cette catégorie.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-2 space-y-2.5 md:mt-4 md:space-y-4">
            {(drillDown?.items || []).map((item: any, i: number) => (
              <div 
                key={i} 
                className="flex min-h-12 items-center justify-between gap-3 p-3 rounded-lg border bg-slate-50/50 cursor-pointer hover:bg-slate-50 transition-colors group"
                onClick={() => {
                  setDrillDown(null)
                  handleAccountClick(item.account_id)
                }}
              >
                <div className="flex min-w-0 flex-col">
                  <span className="font-medium text-sm break-words group-hover:text-slate-600 transition-colors">{item.account_name || "Compte sans nom"}</span>
                  <span className="text-xs text-muted-foreground">{typeof item.percentage_of_group === 'number' ? `${item.percentage_of_group.toFixed(1)}%` : `${item.percentage_of_group || 0}%`} du groupe</span>
                </div>
                <div className="shrink-0 text-right">
                  <span className="whitespace-nowrap font-bold text-sm tabular-nums amount-blur">{formatCurrency(item.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
