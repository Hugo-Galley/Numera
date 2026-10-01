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
  ShieldCheck
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
import { DiversityScannerResponse } from "@/types/diversity"
import { CompanyLogo } from "@/components/ui/CompanyLogo"

const COLORS = ["#000000", "#4b5563", "#9ca3af", "#d1d5db", "#e5e7eb", "#f3f4f6", "#f8fafc"]

export default function Investments() {
  const navigate = useNavigate()
  const [allocation, setAllocation] = useState<any>(null)
  const [advancedAllocation, setAdvancedAllocation] = useState<any>(null)
  const [diversity, setDiversity] = useState<DiversityScannerResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [drillDown, setDrillDown] = useState<{ title: string, items: any[] } | null>(null)

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
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Investissements</h1>
        <p className="text-muted-foreground mt-1">Suivez la performance et la répartition de votre patrimoine investi.</p>
      </div>

      {/* KPI Section */}
      <div className={`grid gap-4 grid-cols-1 ${diversity ? "md:grid-cols-4" : "md:grid-cols-3"}`}>
        <Card className="bg-slate-900 text-white shadow-md border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Valeur Totale</CardTitle>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              <span className="amount-blur">{formatCurrency(allocation?.total_current_value || 0)}</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">Somme des dernières valeurs connues</p>
          </CardContent>
        </Card>
        
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performance Globale</CardTitle>
            <Activity className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${allocation?.total_gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              <span className="amount-blur">
                {allocation?.total_gain_eur >= 0 ? "+" : ""}{formatCurrency(allocation?.total_gain_eur || 0)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {(allocation?.total_performance_pct || 0).toFixed(2)}% de rendement total
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Nombre de supports</CardTitle>
            <Wallet className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{allocation?.items.length || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Comptes d'investissement actifs</p>
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
                <span className="text-3xl font-bold">{diversity.score}</span>
                <span className="text-sm text-muted-foreground">/100</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{diversity.score_label}</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Alerts Section */}
      {diversity && diversity.alerts.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5 text-slate-500" />
            Alertes de Surexposition ({diversity.alerts.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {diversity.alerts.map((alert, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border bg-white flex items-start gap-3 shadow-sm"
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
                <div className="space-y-1">
                  <h4 className="font-semibold text-xs">{alert.title}</h4>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">{alert.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 1: Répartition par comptes */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Répartition par compte</h2>
          <p className="text-sm text-muted-foreground">Vos investissements séparés par enveloppe.</p>
        </div>
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-7">
          <Card className="lg:col-span-4 shadow-sm">
            <CardContent className="h-[350px] p-4">
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
              <CardTitle className="text-base">Détails de l'allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-5">
                {allocation?.items.map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex flex-col gap-1 cursor-pointer hover:bg-slate-50 p-2 -mx-2 rounded-lg transition-colors group"
                    onClick={() => handleAccountClick(item.account_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                        <span className="font-medium text-sm truncate max-w-[150px] sm:max-w-none group-hover:text-slate-600 transition-colors">
                          {item.account_name} 
                          {item.currency && item.currency !== "EUR" && (
                            <span className="text-xs text-muted-foreground ml-1">({item.currency})</span>
                          )}
                        </span>
                      </div>
                      <span className="font-bold text-sm shrink-0">{item.percentage.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground ml-5">
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

      {/* Section 2: Performance détaillée */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Performance détaillée</h2>
          <p className="text-sm text-muted-foreground">Historique et évolution de vos supports.</p>
        </div>
        <Card className="shadow-sm">
          <CardContent className="h-[300px] px-2 sm:px-6 pt-6">
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
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-b">
            <div>
              <CardTitle className="text-base font-bold">Vue d'ensemble de l'allocation</CardTitle>
            </div>
            <Badge variant="secondary" className="bg-slate-100 text-slate-900 pointer-events-none shadow-none border-none">Treemap</Badge>
          </CardHeader>
          <CardContent className="pt-6">
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

        <div className="grid gap-6 grid-cols-1 md:grid-cols-2">
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
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="w-full space-y-1.5 mt-3 px-2">
                {(advancedAllocation?.by_asset_class || []).slice(0, 4).map((item: any, i: number) => (
                  <div 
                    key={i} 
                    className="flex items-center justify-between text-xs cursor-pointer hover:text-slate-600 transition-colors"
                    onClick={() => setDrillDown({ title: `Classe d'actif : ${item.name}`, items: item.items || [] })}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="truncate max-w-[150px]">{item.name}</span>
                    </div>
                    <span className="font-bold">{item.percentage}%</span>
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
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
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
                            <span className="truncate max-w-[150px]">{item.name}</span>
                          </div>
                          <span className="font-bold">{typeof item.percentage === 'number' ? item.percentage.toFixed(1) : item.percentage}%</span>
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
            <CardContent className="pt-6">
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
                        margin={{ top: 5, right: 30, left: 15, bottom: 5 }}
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
                          tick={(tickProps: any) => {
                            const { x, y, payload } = tickProps
                            const comp = topCompaniesData.find((c) => c.name === payload.value)
                            return (
                              <g transform={`translate(${x},${y})`}>
                                <foreignObject x={-135} y={-10} width={130} height={20}>
                                  <div
                                    xmlns="http://www.w3.org/1999/xhtml"
                                    className="flex items-center justify-end gap-1.5 h-full pr-1 overflow-hidden"
                                    title={payload.value}
                                  >
                                    <CompanyLogo
                                      ticker={comp?.ticker}
                                      name={payload.value}
                                      className="h-4 w-4 rounded-xs shrink-0"
                                    />
                                    <span className="text-[11px] font-medium text-slate-700 truncate max-w-[105px]">
                                      {payload.value}
                                    </span>
                                  </div>
                                </foreignObject>
                              </g>
                            )
                          }}
                          axisLine={false}
                          tickLine={false}
                          width={140}
                        />
                        <Tooltip
                          cursor={false}
                          content={({ active, payload, label }: any) => {
                            if (active && payload && payload.length) {
                              const d = payload[0].payload
                              return (
                                <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-md text-xs space-y-1.5 min-w-[210px]">
                                  <div className="flex items-center justify-between border-b pb-1.5 gap-2">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <CompanyLogo
                                        ticker={d.ticker}
                                        name={label || d.name}
                                        className="h-5 w-5 rounded-xs shrink-0"
                                      />
                                      <span className="font-semibold text-slate-900 truncate">{label || d.name}</span>
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
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-slate-500" />
                <CardTitle className="text-base">Répartition Géographique Mondiale</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                {diversity && diversity.countries.length > 0 && (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-600 text-[10px] pointer-events-none shadow-none border-none">Look-Through</Badge>
                )}
                <Badge variant="outline" className="bg-white">Interactif</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="h-[450px] p-0 relative bg-slate-50/30">
            <div className="absolute top-4 left-4 z-10 text-xs text-slate-500 bg-white/90 backdrop-blur shadow-sm px-3 py-1.5 rounded-md border">
              Utilisez la molette pour zoomer • Cliquez-glissez pour déplacer
            </div>
            <WorldMap data={
              diversity && diversity.countries.length > 0
                ? diversity.countries.map(c => ({ name: c.name, value: c.value_eur, percentage: c.percentage_stocks }))
                : (advancedAllocation?.by_geographic_zone || [])
            } />
          </CardContent>
        </Card>
      </div>

      <Dialog open={!!drillDown} onOpenChange={(open) => !open && setDrillDown(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{drillDown?.title}</DialogTitle>
            <DialogDescription>
              Détail des comptes contribuant à cette catégorie.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 space-y-4">
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
                  <span className="font-medium text-sm group-hover:text-slate-600 transition-colors">{item.account_name || "Compte sans nom"}</span>
                  <span className="text-xs text-muted-foreground">{typeof item.percentage_of_group === 'number' ? `${item.percentage_of_group.toFixed(1)}%` : `${item.percentage_of_group || 0}%`} du groupe</span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-sm amount-blur">{formatCurrency(item.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
