import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { 
  TrendingUp, 
  ArrowUpRight, 
  ArrowDownRight, 
  BarChart3,
  PieChart as PieChartIcon,
  Wallet,
  Activity
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
import { WealthSimulator } from "@/components/analytics/WealthSimulator"
import { AllocationTreemap } from "@/components/analytics/AllocationTreemap"

const COLORS = ["#000000", "#4b5563", "#9ca3af", "#d1d5db", "#e5e7eb"]

export default function Investments() {
  const navigate = useNavigate()
  const [allocation, setAllocation] = useState<any>(null)
  const [advancedAllocation, setAdvancedAllocation] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [drillDown, setDrillDown] = useState<{ title: string, items: any[] } | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        const [basic, advanced] = await Promise.all([
          api.get("/analytics/investments-allocation"),
          api.get("/analytics/investments-allocation-advanced")
        ])
        console.log("Investments data:", { basic, advanced });
        setAllocation(basic)
        setAdvancedAllocation(advanced)
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
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Investissements</h1>
        <p className="text-muted-foreground">Suivez la performance et la répartition de votre patrimoine investi.</p>
      </div>

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Valeur Totale</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <span className="amount-blur">{formatCurrency(allocation?.total_current_value || 0)}</span>
            </div>
            <p className="text-xs text-muted-foreground">Somme des dernières valeurs connues</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Nombre de supports</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{allocation?.items.length || 0}</div>
            <p className="text-xs text-muted-foreground">Comptes d'investissement actifs</p>
          </CardContent>
        </Card>
        <Card className="sm:col-span-2 md:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performance Globale</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${allocation?.total_gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              {allocation?.total_gain_eur >= 0 ? "+" : ""}{formatCurrency(allocation?.total_gain_eur || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {(allocation?.total_performance_pct || 0).toFixed(2)}% de rendement total
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-xl font-bold">Allocation</CardTitle>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center bg-slate-100 p-1 rounded-lg">
              <div className="p-1.5 bg-white rounded-md shadow-sm cursor-pointer">
                <BarChart3 className="h-4 w-4 text-slate-900" />
              </div>
              <div className="p-1.5 text-slate-500 cursor-pointer hover:text-slate-900" onClick={() => {
                const pieSection = document.getElementById('pie-allocation-section');
                if (pieSection) pieSection.scrollIntoView({ behavior: 'smooth' });
              }}>
                <PieChartIcon className="h-4 w-4" />
              </div>
            </div>
            <div className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer" onClick={() => navigate("/dashboard")}>
              <ArrowUpRight className="h-4 w-4" />
            </div>
            <Badge 
              variant="secondary" 
              className="bg-slate-100 text-slate-900 hover:bg-slate-200 cursor-pointer px-3 py-1 text-xs font-medium border-none shadow-none"
              onClick={() => navigate("/dashboard")}
            >
              Voir plus
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {advancedAllocation ? (
            <AllocationTreemap 
              data={advancedAllocation.by_asset_class} 
              onItemClick={(node) => setDrillDown({ title: `Classe d'actif : ${node.name}`, items: node.items })}
            />
          ) : (
            <div className="h-[400px] flex items-center justify-center">
              <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
            </div>
          )}
        </CardContent>
      </Card>

      <div id="pie-allocation-section" className="grid gap-4 grid-cols-1 lg:grid-cols-7">
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle>Répartition par compte</CardTitle>
            <CardDescription>Allocation actuelle de vos investissements.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px] sm:h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={window.innerWidth < 640 ? 60 : 80}
                  outerRadius={window.innerWidth < 640 ? 100 : 120}
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
                  formatter={(value: number) => [formatCurrency(value), "Valeur"]}
                  contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Détails de l'allocation</CardTitle>
            <CardDescription>Valeurs et pourcentages.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
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
                    <span>{formatCurrency(item.current_value)}</span>
                    <span className={item.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}>
                      {item.gain_eur >= 0 ? "+" : ""}{formatCurrency(item.gain_eur)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 grid-cols-1 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Par Classe d'actif</CardTitle>
          </CardHeader>
          <CardContent className="h-[250px] flex flex-col items-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={advancedAllocation?.by_asset_class || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={5}
                  dataKey="value"
                  nameKey="name"
                  onClick={(data) => setDrillDown({ title: `Classe d'actif : ${data.name}`, items: data.items })}
                  className="cursor-pointer outline-none"
                >
                  {(advancedAllocation?.by_asset_class || []).map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
              </PieChart>
            </ResponsiveContainer>
            <div className="w-full space-y-1 mt-2">
              {(advancedAllocation?.by_asset_class || []).slice(0, 3).map((item: any, i: number) => (
                <div 
                  key={i} 
                  className="flex items-center justify-between text-[11px] cursor-pointer hover:text-slate-600 transition-colors"
                  onClick={() => setDrillDown({ title: `Classe d'actif : ${item.name}`, items: item.items })}
                >
                  <span className="truncate max-w-[100px]">{item.name}</span>
                  <span className="font-bold">{item.percentage}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Par Secteur</CardTitle>
          </CardHeader>
          <CardContent className="h-[250px] flex flex-col items-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={advancedAllocation?.by_sector || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={5}
                  dataKey="value"
                  nameKey="name"
                  onClick={(data) => setDrillDown({ title: `Secteur : ${data.name}`, items: data.items })}
                  className="cursor-pointer outline-none"
                >
                  {(advancedAllocation?.by_sector || []).map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity" />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
              </PieChart>
            </ResponsiveContainer>
            <div className="w-full space-y-1 mt-2">
              {(advancedAllocation?.by_sector || []).slice(0, 3).map((item: any, i: number) => (
                <div 
                  key={i} 
                  className="flex items-center justify-between text-[11px] cursor-pointer hover:text-slate-600 transition-colors"
                  onClick={() => setDrillDown({ title: `Secteur : ${item.name}`, items: item.items })}
                >
                  <span className="truncate max-w-[100px]">{item.name}</span>
                  <span className="font-bold">{item.percentage}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-4 xl:col-span-5 h-[500px]">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Répartition Géographique Mondiale</CardTitle>
              <CardDescription>Visualisez l'exposition internationale de votre portefeuille.</CardDescription>
            </div>
            <div className="flex gap-2">
               <Badge variant="outline" className="bg-slate-50">Interactif</Badge>
            </div>
          </CardHeader>
          <CardContent className="h-[400px] p-0 relative">
            <div className="absolute top-2 left-4 z-10 text-[10px] text-slate-400 bg-white/50 px-2 py-1 rounded border">
              Utilisez la molette pour zoomer • Cliquez-glissez pour déplacer
            </div>
            <WorldMap data={advancedAllocation?.by_geographic_zone || []} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dernière performance par support</CardTitle>
          <CardDescription>Comparaison de l'évolution de chaque compte.</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] px-2 sm:px-6">
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
                  formatter={(value: number) => [formatCurrency(value), "Valeur"]}
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

      <WealthSimulator initialCapitalDefault={allocation?.total_current_value || 0} />

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
                  <span className="font-medium text-sm group-hover:text-slate-600 transition-colors">{item.account_name}</span>
                  <span className="text-xs text-muted-foreground">{item.percentage_of_group}% du groupe</span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-sm">{formatCurrency(item.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
