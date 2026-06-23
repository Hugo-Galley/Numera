import { useState, useEffect } from "react"
import { 
  TrendingUp, 
  Coins, 
  Percent, 
  Calendar,
  Info,
  Sliders,
  Plus,
  Trash2,
  AlertTriangle,
  Scale,
  Sparkles,
  RefreshCw,
  LineChart as LucideLineChart,
  DollarSign,
  TrendingDown,
  Clock,
  Pencil
} from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line
} from "recharts"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface WealthSimulatorProps {
  initialCapitalDefault?: number
}

interface LifeEvent {
  year: number
  amount: number
  label: string
}

interface AssetClass {
  id: string
  name: string
  pct: number
  expectedReturn: number
  volatility: number
}

const defaultAssetClasses: AssetClass[] = [
  { id: "1", name: "Actions / ETF World", pct: 60, expectedReturn: 8, volatility: 15 },
  { id: "2", name: "Obligations d'État", pct: 20, expectedReturn: 3.5, volatility: 5 },
  { id: "3", name: "Immobilier SCPI", pct: 10, expectedReturn: 5.5, volatility: 8 },
  { id: "4", name: "Cash / Fonds Euro", pct: 10, expectedReturn: 2, volatility: 0 }
]

export function WealthSimulator({ initialCapitalDefault = 10000 }: WealthSimulatorProps) {
  // Load initial params from localStorage if available, else fall back to defaults
  const [params, setParams] = useState(() => {
    const saved = localStorage.getItem("numera_wealth_sim_params")
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        return {
          ...parsed,
          initial_capital: initialCapitalDefault // Reset initial capital default if prop changes
        }
      } catch {}
    }
    return {
      initial_capital: initialCapitalDefault,
      monthly_contribution: 500,
      annual_return_pct: 7,
      years: 20,
      volatility_pct: 0,
      inflation_rate_pct: 2.0,
      contribution_indexation_pct: 0,
      tax_rate_pct: 0,
      tax_deferred: true,
    }
  })

  const [events, setEvents] = useState<LifeEvent[]>(() => {
    const saved = localStorage.getItem("numera_wealth_sim_events")
    if (saved) {
      try { return JSON.parse(saved) } catch {}
    }
    return []
  })

  const [newEvent, setNewEvent] = useState<LifeEvent>({
    year: 5,
    amount: -10000,
    label: ""
  })

  // Asset Allocation State
  const [useAllocation, setUseAllocation] = useState(() => {
    return localStorage.getItem("numera_wealth_sim_use_alloc") === "true"
  })

  const [assetClasses, setAssetClasses] = useState<AssetClass[]>(() => {
    const saved = localStorage.getItem("numera_wealth_sim_asset_classes")
    if (saved) {
      try { return JSON.parse(saved) } catch {}
    }
    return defaultAssetClasses
  })

  const [editingAsset, setEditingAsset] = useState<AssetClass | null>(null)

  // UI state for display
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [showInflationAdjusted, setShowInflationAdjusted] = useState(false)
  const [showMonteCarlo, setShowMonteCarlo] = useState(true)

  // Weighted asset class parameters:
  const totalAlloc = assetClasses.reduce((sum, item) => sum + item.pct, 0)
  const computedReturn = Number(
    (assetClasses.reduce((sum, item) => sum + (item.pct * item.expectedReturn), 0) / 100).toFixed(2)
  )
  const computedVolatility = Number(
    (assetClasses.reduce((sum, item) => sum + (item.pct * item.volatility), 0) / 100).toFixed(2)
  )

  // Sync to local storage
  useEffect(() => {
    localStorage.setItem("numera_wealth_sim_params", JSON.stringify(params))
  }, [params])

  useEffect(() => {
    localStorage.setItem("numera_wealth_sim_events", JSON.stringify(events))
  }, [events])

  useEffect(() => {
    localStorage.setItem("numera_wealth_sim_use_alloc", String(useAllocation))
  }, [useAllocation])

  useEffect(() => {
    localStorage.setItem("numera_wealth_sim_asset_classes", JSON.stringify(assetClasses))
  }, [assetClasses])

  // Sync initialCapitalDefault if it changes from parent
  useEffect(() => {
    setParams(prev => ({ ...prev, initial_capital: initialCapitalDefault }))
  }, [initialCapitalDefault])

  // Main data fetcher
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        let returnPct = params.annual_return_pct
        let volPct = params.volatility_pct

        if (useAllocation) {
          if (totalAlloc === 100) {
            returnPct = computedReturn
            volPct = computedVolatility
          } else {
            // Wait for allocation to equal 100% to avoid rendering inconsistent data
            setLoading(false)
            return
          }
        }

        const queryParams = new URLSearchParams({
          initial_capital: params.initial_capital.toString(),
          monthly_contribution: params.monthly_contribution.toString(),
          annual_return_pct: returnPct.toString(),
          years: params.years.toString(),
          volatility_pct: volPct.toString(),
          inflation_rate_pct: params.inflation_rate_pct.toString(),
          contribution_indexation_pct: params.contribution_indexation_pct.toString(),
          tax_rate_pct: params.tax_rate_pct.toString(),
          tax_deferred: params.tax_deferred.toString(),
          events: JSON.stringify(events.filter(e => e.year <= params.years))
        })

        const res = await api.get(`/analytics/wealth-simulation?${queryParams.toString()}`)
        setData(res)
      } catch (error) {
        toast.error("Erreur lors de la simulation")
      } finally {
        setLoading(false)
      }
    }

    const timeoutId = setTimeout(fetchData, 400)
    return () => clearTimeout(timeoutId)
  }, [params, events, useAllocation, assetClasses, totalAlloc, computedReturn, computedVolatility])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", { 
      style: "currency", 
      currency: "EUR",
      maximumFractionDigits: 0
    }).format(value)
  }

  const handleAddEvent = () => {
    if (!newEvent.label.trim()) {
      toast.error("Veuillez saisir un libellé pour l'événement.")
      return
    }
    if (newEvent.year < 1 || newEvent.year > params.years) {
      toast.error(`L'année de l'événement doit être comprise entre 1 et ${params.years}.`)
      return
    }
    setEvents(prev => [...prev, newEvent].sort((a, b) => a.year - b.year))
    setNewEvent({ year: Math.min(newEvent.year + 1, params.years), amount: -10000, label: "" })
    toast.success("Événement ajouté à la simulation")
  }

  const handleRemoveEvent = (index: number) => {
    setEvents(prev => prev.filter((_, i) => i !== index))
    toast.success("Événement supprimé")
  }

  const updateAsset = (id: string, updates: Partial<AssetClass>) => {
    setAssetClasses(prev => prev.map(item => {
      if (item.id === id) {
        return { ...item, ...updates }
      }
      return item
    }))
  }

  const handleAddAsset = () => {
    const newId = String(Date.now())
    const newClass = { id: newId, name: "Nouvelle classe d'actifs", pct: 0, expectedReturn: 6, volatility: 10 }
    setAssetClasses(prev => [...prev, newClass])
    setEditingAsset(newClass)
  }

  const handleDeleteAsset = (id: string) => {
    if (assetClasses.length <= 1) {
      toast.error("Vous devez conserver au moins une classe d'actifs.")
      return
    }
    setAssetClasses(prev => prev.filter(item => item.id !== id))
    toast.success("Actif supprimé")
  }

  const handlePresetAllocation = (preset: "balanced_60_40" | "all_actions" | "all_weather" | "crypto_tilted") => {
    if (preset === "balanced_60_40") {
      setAssetClasses([
        { id: "1", name: "Actions / ETF World", pct: 60, expectedReturn: 8, volatility: 15 },
        { id: "2", name: "Obligations d'État", pct: 40, expectedReturn: 3.5, volatility: 5 }
      ])
    } else if (preset === "all_actions") {
      setAssetClasses([
        { id: "1", name: "Actions / ETF", pct: 100, expectedReturn: 8.5, volatility: 16 }
      ])
    } else if (preset === "all_weather") {
      setAssetClasses([
        { id: "1", name: "Actions ETF World", pct: 30, expectedReturn: 8, volatility: 15 },
        { id: "2", name: "Obligations LT", pct: 40, expectedReturn: 4, volatility: 7 },
        { id: "3", name: "Obligations MT", pct: 15, expectedReturn: 3, volatility: 4 },
        { id: "4", name: "Matières Premières / Or", pct: 15, expectedReturn: 5, volatility: 12 }
      ])
    } else if (preset === "crypto_tilted") {
      setAssetClasses([
        { id: "1", name: "ETF Actions World", pct: 70, expectedReturn: 8, volatility: 15 },
        { id: "2", name: "Cryptomonnaies (BTC/ETH)", pct: 10, expectedReturn: 25, volatility: 60 },
        { id: "3", name: "Assurance-Vie / Fonds Euro", pct: 20, expectedReturn: 2.5, volatility: 0 }
      ])
    }
    toast.success("Preset d'allocation appliqué")
  }

  const isVolatile = useAllocation ? computedVolatility > 0 : params.volatility_pct > 0
  const activeEventsCount = events.filter(e => e.year <= params.years).length

  // Custom tooltips for Recharts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload
      const eventStr = point.event_applied
      
      return (
        <div className="bg-white p-3 border rounded-lg shadow-md text-xs space-y-2 max-w-[280px]">
          <p className="font-bold border-b pb-1">Année {label}</p>
          
          {isVolatile && showMonteCarlo ? (
            <div className="space-y-1">
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Optimiste (P90):</span>
                <span className="font-semibold text-emerald-600 amount-blur">
                  {formatCurrency(showInflationAdjusted ? point.total_value_p90_real : point.total_value_p90)}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Médian (P50):</span>
                <span className="font-bold text-indigo-600 amount-blur">
                  {formatCurrency(showInflationAdjusted ? point.total_value_p50_real : point.total_value_p50)}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Pessimiste (P10):</span>
                <span className="font-semibold text-rose-600 amount-blur">
                  {formatCurrency(showInflationAdjusted ? point.total_value_p10_real : point.total_value_p10)}
                </span>
              </div>
              <div className="border-t pt-1 mt-1 flex justify-between gap-4 text-[10px] text-slate-400">
                <span>Versements cum.:</span>
                <span className="amount-blur">{formatCurrency(point.total_contributions)}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Capital Initial:</span>
                <span className="font-medium amount-blur">{formatCurrency(point.initial_capital)}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Versements:</span>
                <span className="font-medium amount-blur">{formatCurrency(point.total_contributions)}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Intérêts (Nets):</span>
                <span className="font-medium text-emerald-600 amount-blur">{formatCurrency(point.total_interest)}</span>
              </div>
              {point.total_tax_paid > 0 && (
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500">Impôts dues:</span>
                  <span className="font-medium text-rose-600 amount-blur">-{formatCurrency(point.total_tax_paid)}</span>
                </div>
              )}
              <div className="pt-1 mt-1 border-t flex justify-between gap-4">
                <span className="font-bold">Total (Nominal):</span>
                <span className="font-bold amount-blur">{formatCurrency(point.total_value)}</span>
              </div>
              {showInflationAdjusted && (
                <div className="flex justify-between gap-4 text-slate-500">
                  <span>Total (Réel/Ajusté):</span>
                  <span className="font-bold amount-blur">{formatCurrency(point.total_value_real)}</span>
                </div>
              )}
            </div>
          )}
          
          {eventStr && (
            <div className="mt-1.5 pt-1.5 border-t border-dashed border-slate-200 text-amber-600 font-medium text-[10px] flex items-start gap-1">
              <Info className="h-3 w-3 mt-0.5 shrink-0" />
              <span>Événement : {eventStr}</span>
            </div>
          )}
        </div>
      )
    }
    return null
  }

  return (
    <Card className="w-full border-slate-200 shadow-sm">
      <CardHeader className="pb-4 border-b border-slate-100 bg-slate-50/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold text-slate-900">Simulateur de Patrimoine Avancé</CardTitle>
              <CardDescription>
                Projetez votre stratégie d'investissement avec volatilité, inflation, fiscalité et accidents de parcours.
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start md:self-auto">
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />}
            {isVolatile && <Badge className="bg-purple-50 text-purple-700 border-purple-200">Monte Carlo Actif</Badge>}
            {showInflationAdjusted && <Badge className="bg-red-50 text-red-700 border-red-200">Euros Constants</Badge>}
          </div>
        </div>
      </CardHeader>

      <Tabs defaultValue="base" className="w-full">
        <CardContent className="pt-6 space-y-6">
          
          {/* 1. CHOIX DE PARAMETRES EN HAUT (TabsList) */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <TabsList className="bg-slate-100 p-1 rounded-lg shrink-0 flex flex-wrap gap-0.5">
              <TabsTrigger value="base" className="text-xs py-1.5 px-3">Général</TabsTrigger>
              <TabsTrigger value="allocation" className="text-xs py-1.5 px-3">Allocation d'Actifs</TabsTrigger>
              <TabsTrigger value="advanced" className="text-xs py-1.5 px-3">Fiscalité & Risque</TabsTrigger>
              <TabsTrigger value="events" className="text-xs py-1.5 px-3 relative">
                Événements de Vie
                {activeEventsCount > 0 && (
                  <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-[9px] font-bold text-white">
                    {activeEventsCount}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>
            
            <div className="flex items-center gap-2 text-xs text-slate-500 font-semibold bg-indigo-50/50 border border-indigo-100/50 rounded-lg py-1.5 px-3">
              <span>Configuration active : </span>
              {useAllocation ? (
                <span className="text-indigo-700 font-bold">Allocation d'actifs ({computedReturn}% rdt / {computedVolatility}% vol)</span>
              ) : (
                <span className="text-indigo-700 font-bold">Saisie manuelle ({params.annual_return_pct}% rdt / {params.volatility_pct}% vol)</span>
              )}
            </div>
          </div>

          {/* 2. GRILLE PRINCIPALE (A GAUCHE: INPUTS + TABLEAU DET, A DROITE: KPIs + GRAPHIQUE) */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
            
            {/* COLONNE GAUCHE (5 COLS) : CONTROLEURS + TABLEAU DET */}
            <div className="xl:col-span-5 space-y-6">
              
              {/* CADRE DES INPUTS DE L'ONGLET ACTIF */}
              <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 shadow-sm space-y-4">
                
                {/* CONTENU ONGLET 1: GENERAL */}
                <TabsContent value="base" className="space-y-4 m-0 outline-none">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="initial_capital" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Coins className="h-3.5 w-3.5 text-slate-400" />
                        Capital Initial
                      </Label>
                      <Input
                        id="initial_capital"
                        type="number"
                        value={params.initial_capital}
                        onChange={(e) => setParams({ ...params, initial_capital: Number(e.target.value) })}
                        className="h-9 bg-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="monthly_contribution" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" />
                        Versement Mensuel
                      </Label>
                      <Input
                        id="monthly_contribution"
                        type="number"
                        value={params.monthly_contribution}
                        onChange={(e) => setParams({ ...params, monthly_contribution: Number(e.target.value) })}
                        className="h-9 bg-white"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="years" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        Durée (années)
                      </Label>
                      <Input
                        id="years"
                        type="number"
                        min={1}
                        max={50}
                        value={params.years}
                        onChange={(e) => setParams({ ...params, years: Number(e.target.value) })}
                        className="h-9 bg-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="annual_return_pct" className="flex items-center justify-between text-xs font-semibold text-slate-700">
                        <span className="flex items-center gap-1.5">
                          <Percent className="h-3.5 w-3.5 text-slate-400" />
                          Rendement Annuel (%)
                        </span>
                        {useAllocation && (
                          <Badge variant="outline" className="text-[9px] text-emerald-600 bg-emerald-50/50 border-emerald-200">Calculé</Badge>
                        )}
                      </Label>
                      <Input
                        id="annual_return_pct"
                        type="number"
                        step="0.1"
                        disabled={useAllocation}
                        value={useAllocation ? computedReturn : params.annual_return_pct}
                        onChange={(e) => setParams({ ...params, annual_return_pct: Number(e.target.value) })}
                        className="h-9 bg-white"
                      />
                    </div>
                  </div>
                </TabsContent>

                {/* CONTENU ONGLET 2: ALLOCATION D'ACTIFS */}
                <TabsContent value="allocation" className="space-y-4 m-0 outline-none">
                  <div className="flex items-center justify-between bg-white p-2.5 rounded-lg border border-slate-100 shadow-sm">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-xs font-bold text-slate-800">Simuler selon une allocation d'actifs</span>
                      <span className="text-[10px] text-slate-400">Rendement et risque calculés selon les pondérations</span>
                    </div>
                    <Switch 
                      checked={useAllocation}
                      onCheckedChange={setUseAllocation}
                    />
                  </div>

                  {useAllocation ? (
                    <div className="space-y-4 pt-1">
                      
                      {/* PRESETS D'ALLOCATION */}
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Presets d'allocations</span>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-1.5">
                          <button type="button" onClick={() => handlePresetAllocation("balanced_60_40")} className="text-[10px] font-semibold py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">60/40 Portefeuille</button>
                          <button type="button" onClick={() => handlePresetAllocation("all_actions")} className="text-[10px] font-semibold py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">100% Actions</button>
                          <button type="button" onClick={() => handlePresetAllocation("all_weather")} className="text-[10px] font-semibold py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">All-Weather</button>
                          <button type="button" onClick={() => handlePresetAllocation("crypto_tilted")} className="text-[10px] font-semibold py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">Crypto Tilted</button>
                        </div>
                      </div>

                      {/* LISTE PROPRE DES SLIDERS AVEC CRAYON D'EDITION */}
                      <div className="space-y-3.5 max-h-[290px] overflow-y-auto pr-1">
                        {assetClasses.map(item => (
                          <div key={item.id} className="space-y-1.5 bg-white p-3 rounded-lg border border-slate-100 shadow-sm relative group hover:border-slate-300 transition-all">
                            <div className="flex justify-between items-center text-xs">
                              <span className="font-semibold text-slate-755">{item.name} ({item.pct}%)</span>
                              <div className="flex items-center gap-1">
                                <span className="text-[10px] text-slate-400 mr-1">Rdt: {item.expectedReturn}% | Vol: {item.volatility}%</span>
                                <button
                                  type="button"
                                  onClick={() => setEditingAsset(item)}
                                  className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-slate-800 transition-colors"
                                  title="Modifier les hypothèses de cet actif"
                                >
                                  <Pencil className="h-3 w-3" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteAsset(item.id)}
                                  className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-rose-600 transition-colors"
                                  title="Supprimer cet actif"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              </div>
                            </div>
                            
                            {/* Simple weight slider */}
                            <div className="pt-1">
                              <input 
                                type="range" min="0" max="100" step="1" value={item.pct}
                                onChange={(e) => updateAsset(item.id, { pct: Number(e.target.value) })}
                                className="w-full accent-indigo-650 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                              />
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* AJOUT CLASSE D'ACTIF */}
                      <button
                        type="button"
                        onClick={handleAddAsset}
                        className="w-full border border-dashed border-indigo-200 hover:border-indigo-400 text-indigo-650 hover:bg-indigo-50/50 rounded-lg py-2 text-xs font-bold transition-all flex items-center justify-center gap-1"
                      >
                        <Plus className="h-4 w-4" />
                        Ajouter une classe d'actifs
                      </button>

                      {/* STATUT PONDERATION */}
                      <div className="flex items-center justify-between text-xs px-1 border-t border-slate-100 pt-3">
                        <span className="font-semibold text-slate-600">Pondération totale :</span>
                        <span className={`font-bold ${totalAlloc === 100 ? "text-emerald-600" : "text-rose-600"}`}>
                          {totalAlloc}% {totalAlloc === 100 ? "✓" : "(doit être de 100%)"}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-xs text-slate-400 bg-white border border-dashed rounded-lg">
                      Activez le commutateur ci-dessus pour utiliser une allocation d'actifs personnalisable.
                    </div>
                  )}
                </TabsContent>

                {/* CONTENU ONGLET 3: RISQUE ET FISCALITE */}
                <TabsContent value="advanced" className="space-y-4 m-0 outline-none">
                  <div className="space-y-2">
                    <Label htmlFor="volatility_pct" className="flex items-center justify-between text-xs font-semibold text-slate-700">
                      <span className="flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5 text-slate-400" />
                        Volatilité Annuelle (%)
                      </span>
                      {useAllocation && (
                        <Badge variant="outline" className="text-[9px] text-emerald-600 bg-emerald-50/50 border-emerald-200">Calculé</Badge>
                      )}
                    </Label>
                    <Input
                      id="volatility_pct"
                      type="number"
                      step="0.5"
                      disabled={useAllocation}
                      value={useAllocation ? computedVolatility : params.volatility_pct}
                      onChange={(e) => setParams({ ...params, volatility_pct: Number(e.target.value) })}
                      className="h-9 bg-white"
                    />
                    <p className="text-[10px] text-slate-400 leading-normal">
                      Une volatilité supérieure à 0% déclenche une simulation de Monte Carlo avec 1000 tirages mensuels aléatoires.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="inflation_rate_pct" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <TrendingDown className="h-3.5 w-3.5 text-slate-400" />
                        Inflation Annuelle (%)
                      </Label>
                      <Input
                        id="inflation_rate_pct"
                        type="number"
                        step="0.1"
                        value={params.inflation_rate_pct}
                        onChange={(e) => setParams({ ...params, inflation_rate_pct: Number(e.target.value) })}
                        className="h-9 bg-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="contribution_indexation_pct" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Plus className="h-3.5 w-3.5 text-slate-400" />
                        Indexation Versements (%)
                      </Label>
                      <Input
                        id="contribution_indexation_pct"
                        type="number"
                        step="0.5"
                        value={params.contribution_indexation_pct}
                        onChange={(e) => setParams({ ...params, contribution_indexation_pct: Number(e.target.value) })}
                        className="h-9 bg-white"
                      />
                    </div>
                  </div>

                  <div className="border-t border-slate-200 pt-3 space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="tax_rate_pct" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                          <Scale className="h-3.5 w-3.5 text-slate-400" />
                          Taux d'Impôt (%)
                        </Label>
                        <Input
                          id="tax_rate_pct"
                          type="number"
                          step="1"
                          value={params.tax_rate_pct}
                          onChange={(e) => setParams({ ...params, tax_rate_pct: Number(e.target.value) })}
                          className="h-9 bg-white"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="tax_deferred" className="text-xs font-semibold text-slate-700">
                          Régime Fiscal
                        </Label>
                        <select
                          id="tax_deferred"
                          value={params.tax_deferred ? "true" : "false"}
                          onChange={(e) => setParams({ ...params, tax_deferred: e.target.value === "true" })}
                          className="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950"
                        >
                          <option value="true">Capitalisation (PEA / Assur-vie)</option>
                          <option value="false">Prélèvement Annuel (Compte-titres)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* CONTENU ONGLET 4: EVENEMENTS DE VIE */}
                <TabsContent value="events" className="space-y-4 m-0 outline-none">
                  <div className="bg-white p-3 rounded-lg border border-slate-150 shadow-inner space-y-3">
                    <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
                      <Plus className="h-3.5 w-3.5 text-indigo-600" />
                      Ajouter un événement (achat, héritage...)
                    </span>
                    
                    <div className="grid grid-cols-3 gap-2">
                      <div className="col-span-2 space-y-1">
                        <Label className="text-[10px]">Libellé</Label>
                        <Input
                          placeholder="Achat voiture, Achat RP..."
                          value={newEvent.label}
                          onChange={(e) => setNewEvent({ ...newEvent, label: e.target.value })}
                          className="h-8 text-xs bg-slate-50/50"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-[10px]">Année</Label>
                        <Input
                          type="number"
                          min={1}
                          max={params.years}
                          value={newEvent.year}
                          onChange={(e) => setNewEvent({ ...newEvent, year: Math.min(Number(e.target.value), params.years) })}
                          className="h-8 text-xs bg-slate-50/50"
                        />
                      </div>
                    </div>

                    <div className="flex gap-2 items-end justify-between">
                      <div className="space-y-1 flex-1">
                        <Label className="text-[10px]">Montant (€) (négatif = dépense)</Label>
                        <Input
                          type="number"
                          placeholder="Ex: -25000"
                          value={newEvent.amount}
                          onChange={(e) => setNewEvent({ ...newEvent, amount: Number(e.target.value) })}
                          className="h-8 text-xs bg-slate-50/50"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={handleAddEvent}
                        className="bg-indigo-600 text-white rounded px-3 py-1.5 text-xs font-semibold hover:bg-indigo-700 h-8 flex items-center gap-1 shrink-0"
                      >
                        Ajouter
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
                    <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Événements ajoutés ({activeEventsCount})</h4>
                    
                    {activeEventsCount === 0 ? (
                      <div className="text-center py-4 border border-dashed rounded text-[11px] text-slate-400 bg-white">
                        Aucun événement ponctuel configuré.
                      </div>
                    ) : (
                      events
                        .filter(e => e.year <= params.years)
                        .map((ev, index) => (
                          <div key={index} className="flex justify-between items-center p-2 border bg-white rounded-md text-xs hover:border-slate-300 group">
                            <div className="flex flex-col gap-0.5">
                              <span className="font-semibold text-slate-700">{ev.label}</span>
                              <span className="text-[10px] text-slate-455">Année {ev.year}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className={`font-bold ${ev.amount >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                {ev.amount >= 0 ? "+" : ""}{formatCurrency(ev.amount)}
                              </span>
                              <button
                                type="button"
                                onClick={() => handleRemoveEvent(index)}
                                className="text-slate-400 hover:text-rose-650 opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                        ))
                    )}
                  </div>
                </TabsContent>

              </div>

              {/* TABLEAU DETAILLE DES MONTANTS */}
              <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm">
                <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex justify-between items-center">
                  <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5 text-slate-500" />
                    Tableau annuel détaillé
                  </span>
                  <span className="text-[10px] text-slate-400">Montants nets d'impôts</span>
                </div>
                <div className="max-h-[290px] overflow-y-auto">
                  <Table>
                    <TableHeader className="bg-slate-50/90 sticky top-0 z-10 shadow-[0_1px_0_rgba(0,0,0,0.05)] backdrop-blur-sm">
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="w-16 py-1.5 text-[10px] font-bold text-slate-550 uppercase">Année</TableHead>
                        <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Total (Nom.)</TableHead>
                        <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Total (Réel)</TableHead>
                        <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Versements</TableHead>
                        <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Intérêts</TableHead>
                        <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Événement</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data?.items?.map((item: any) => (
                        <TableRow key={item.year} className="hover:bg-slate-50/50">
                          <TableCell className="font-medium text-[11px] py-1.5">{item.year}</TableCell>
                          <TableCell className="text-right font-semibold text-[11px] py-1.5 amount-blur text-indigo-600">
                            {formatCurrency(item.total_value)}
                          </TableCell>
                          <TableCell className="text-right text-[11px] py-1.5 amount-blur text-slate-655">
                            {formatCurrency(item.total_value_real)}
                          </TableCell>
                          <TableCell className="text-right text-[11px] py-1.5 amount-blur text-slate-500">
                            {formatCurrency(item.total_contributions)}
                          </TableCell>
                          <TableCell className="text-right text-[11px] py-1.5 amount-blur text-emerald-600">
                            {formatCurrency(item.total_interest)}
                          </TableCell>
                          <TableCell className="text-right text-[10px] py-1.5 text-amber-600 max-w-[110px] truncate" title={item.event_applied}>
                            {item.event_applied || "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

            </div>

            {/* COLONNE DROITE (7 COLS) : KPIs + GRAPHIQUE + INFOS */}
            <div className="xl:col-span-7 space-y-6">
              
              {/* BLOC DES METRICS KPIs */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                {/* KPI 1 : PATRIMOINE TOTAL FINAL */}
                <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 flex flex-col justify-between shadow-sm relative overflow-hidden">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Patrimoine Final</span>
                    <Badge variant="secondary" className="bg-indigo-50 text-indigo-700 text-[9px] hover:bg-indigo-50 border-none font-bold">Médian</Badge>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-2xl font-black text-indigo-650 amount-blur">
                      {formatCurrency(data?.total_final || 0)}
                    </span>
                    <span className="text-[9px] text-slate-400 mt-1 leading-normal">
                      {params.inflation_rate_pct > 0 && data?.total_final_real ? (
                        <>Soit <span className="amount-blur font-semibold text-slate-655">{formatCurrency(data.total_final_real)}</span> en pouvoir d'achat</>
                      ) : (
                        "Pouvoir d'achat nominal"
                      )}
                    </span>
                  </div>
                </div>

                {/* KPI 2 : TOTAL VERSEMENTS (EPARGNE CUMULEE) */}
                <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 flex flex-col justify-between shadow-sm">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Cumul Épargné</span>
                    <Calendar className="h-3.5 w-3.5 text-slate-400" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-2xl font-black text-slate-700 amount-blur">
                      {formatCurrency((params.initial_capital || 0) + (data?.total_contributions || 0))}
                    </span>
                    <span className="text-[9px] text-slate-400 mt-1 leading-normal">
                      Dont <span className="amount-blur font-semibold text-slate-655">{formatCurrency(params.initial_capital)}</span> de départ
                    </span>
                  </div>
                </div>

                {/* KPI 3 : PLUS-VALUES ET GAINS GENERES */}
                <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 flex flex-col justify-between shadow-sm">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Plus-values Nettes</span>
                    <span className="text-[9px] text-emerald-700 font-bold bg-emerald-50 px-1 rounded border border-emerald-100">Gains</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-2xl font-black text-emerald-600 amount-blur">
                      +{formatCurrency(data?.total_interest || 0)}
                    </span>
                    <span className="text-[9px] text-slate-400 mt-1 leading-normal">
                      {params.tax_rate_pct > 0 && data?.total_tax_paid ? (
                        <>Taxes estimées : <span className="amount-blur font-semibold text-rose-500">-{formatCurrency(data.total_tax_paid)}</span></>
                      ) : (
                        "Exonéré d'impôt"
                      )}
                    </span>
                  </div>
                </div>
              </div>

              {/* BANNIÈRE DE DISTRIBUTION DES SCÉNARIOS MONTE CARLO */}
              {isVolatile && data && (
                <div className="grid grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-100 shadow-sm">
                  <div className="flex flex-col">
                    <span className="text-[9px] text-rose-550 uppercase font-bold tracking-wider flex items-center gap-1">
                      <TrendingDown className="h-3 w-3" />
                      Scénario Catastrophe (P10)
                    </span>
                    <span className="text-base font-black text-rose-600 amount-blur mt-1">
                      {formatCurrency(showInflationAdjusted ? data.items[data.items.length - 1].total_value_p10_real : data.pessimistic_final)}
                    </span>
                    <span className="text-[9px] text-slate-455 mt-0.5">90% de chances de dépasser ce montant</span>
                  </div>
                  <div className="flex flex-col border-l border-slate-200 pl-4">
                    <span className="text-[9px] text-emerald-600 uppercase font-bold tracking-wider flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      Scénario Idéal (P90)
                    </span>
                    <span className="text-base font-black text-emerald-600 amount-blur mt-1">
                      {formatCurrency(showInflationAdjusted ? data.items[data.items.length - 1].total_value_p90_real : data.optimistic_final)}
                    </span>
                    <span className="text-[9px] text-slate-455 mt-0.5">10% de chances de dépasser ce montant</span>
                  </div>
                </div>
              )}

              {/* EN-TETE ET FILTRES D'AFFICHAGE DU GRAPHIQUE */}
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-3">
                <h3 className="text-xs font-bold text-slate-700 flex items-center gap-1">
                  <LucideLineChart className="h-3.5 w-3.5 text-slate-500" />
                  Courbe de projection patrimoniale
                </h3>
                
                <div className="flex items-center gap-4">
                  {params.inflation_rate_pct !== 0 && (
                    <div className="flex items-center gap-1.5">
                      <Switch
                        id="toggle-inflation"
                        checked={showInflationAdjusted}
                        onCheckedChange={setShowInflationAdjusted}
                        className="scale-75"
                      />
                      <Label htmlFor="toggle-inflation" className="text-[11px] font-semibold cursor-pointer text-slate-600">
                        Ajuster inflation
                      </Label>
                    </div>
                  )}
                  
                  {isVolatile && (
                    <div className="flex items-center gap-1.5">
                      <Switch
                        id="toggle-montecarlo"
                        checked={showMonteCarlo}
                        onCheckedChange={setShowMonteCarlo}
                        className="scale-75"
                      />
                      <Label htmlFor="toggle-montecarlo" className="text-[11px] font-semibold cursor-pointer text-slate-600">
                        Montrer scénarios
                      </Label>
                    </div>
                  )}
                </div>
              </div>

              {/* GRAPHIQUE RECHARTS PRINCIPAL */}
              <div className="h-[360px] w-full bg-white rounded-xl border border-slate-50 p-2 shadow-inner">
                <ResponsiveContainer width="100%" height="100%">
                  {isVolatile && showMonteCarlo ? (
                    <LineChart data={data?.items || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f8fafc" />
                      <XAxis 
                        dataKey="year" 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                        tickFormatter={(val) => `${(val / 1000).toFixed(0)}k€`}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: 10 }} />
                      <Line
                        type="monotone"
                        dataKey={showInflationAdjusted ? "total_value_p90_real" : "total_value_p90"}
                        name="Optimiste (P90)"
                        stroke="#10b981"
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey={showInflationAdjusted ? "total_value_p50_real" : "total_value_p50"}
                        name="Médian (P50)"
                        stroke="#6366f1"
                        strokeWidth={2.5}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey={showInflationAdjusted ? "total_value_p10_real" : "total_value_p10"}
                        name="Pessimiste (P10)"
                        stroke="#f43f5e"
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        dot={false}
                      />
                    </LineChart>
                  ) : (
                    <AreaChart data={data?.items || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorInterest" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.15}/>
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorContributions" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f8fafc" />
                      <XAxis 
                        dataKey="year" 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                        tickFormatter={(val) => `${(val / 1000).toFixed(0)}k€`}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: 10 }} />
                      <Area
                        type="monotone"
                        dataKey="initial_capital"
                        name="Capital Initial"
                        stackId="1"
                        stroke="#94a3b8"
                        fill="#f1f5f9"
                        fillOpacity={0.8}
                      />
                      <Area
                        type="monotone"
                        dataKey="total_contributions"
                        name="Versements"
                        stackId="1"
                        stroke="#3b82f6"
                        fill="url(#colorContributions)"
                      />
                      <Area
                        type="monotone"
                        dataKey="total_interest"
                        name="Intérêts"
                        stackId="1"
                        stroke="#10b981"
                        fill="url(#colorInterest)"
                      />
                      {showInflationAdjusted && (
                        <Line
                          type="monotone"
                          dataKey="total_value_real"
                          name="Total Réel (Inflation)"
                          stroke="#ef4444"
                          strokeWidth={2}
                          strokeDasharray="5 5"
                          dot={false}
                        />
                      )}
                    </AreaChart>
                  )}
                </ResponsiveContainer>
              </div>

              {/* PETIT DECHARGE LEGAL / NOTES TECHNIQUE */}
              <div className="flex items-start gap-2 text-[10px] text-slate-400 bg-slate-50/50 p-2.5 rounded-lg border border-slate-100 border-dashed">
                <Info className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
                <p className="leading-relaxed">
                  Calculs financiers sous-jacents basés sur une composition mensuelle. Les prévisions de Monte Carlo utilisent des écarts-types normaux basés sur les classes d'actifs ou entrées manuelles. 
                  Ces courbes sont informatives et ne présagent pas de la performance future de vos capitaux réels.
                </p>
              </div>

            </div>

          </div>
        </CardContent>
      </Tabs>

      {/* POPUP DE MODIFICATION D'UNE CLASSE D'ACTIFS */}
      {editingAsset && (
        <Dialog open={!!editingAsset} onOpenChange={(open) => { if (!open) setEditingAsset(null) }}>
          <DialogContent className="sm:max-w-[400px] bg-white border border-slate-200 shadow-xl rounded-lg">
            <DialogHeader>
              <DialogTitle className="text-sm font-bold text-slate-900">Modifier l'actif</DialogTitle>
              <DialogDescription className="text-xs text-slate-500">
                Ajustez les paramètres de rendement et de risque pour cette classe d'actifs.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-3">
              <div className="space-y-1">
                <Label htmlFor="edit-name" className="text-xs font-semibold text-slate-700">Nom de l'actif</Label>
                <Input
                  id="edit-name"
                  value={editingAsset.name}
                  onChange={(e) => setEditingAsset({ ...editingAsset, name: e.target.value })}
                  className="h-9 text-xs"
                  placeholder="Ex: Actions ETF World, Assurance-vie..."
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor="edit-return" className="text-xs font-semibold text-slate-700">Rendement Moyen (%)</Label>
                  <Input
                    id="edit-return"
                    type="number"
                    step="0.1"
                    value={editingAsset.expectedReturn}
                    onChange={(e) => setEditingAsset({ ...editingAsset, expectedReturn: Number(e.target.value) })}
                    className="h-9 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="edit-volatility" className="text-xs font-semibold text-slate-700">Volatilité (%)</Label>
                  <Input
                    id="edit-volatility"
                    type="number"
                    step="0.5"
                    value={editingAsset.volatility}
                    onChange={(e) => setEditingAsset({ ...editingAsset, volatility: Number(e.target.value) })}
                    className="h-9 text-xs"
                  />
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 mt-2">
              <button
                type="button"
                onClick={() => setEditingAsset(null)}
                className="border border-slate-200 rounded px-3 py-1.5 text-xs font-semibold hover:bg-slate-50 text-slate-705 h-9 transition-colors"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={() => {
                  updateAsset(editingAsset.id, {
                    name: editingAsset.name,
                    expectedReturn: editingAsset.expectedReturn,
                    volatility: editingAsset.volatility
                  })
                  setEditingAsset(null)
                  toast.success("Actif mis à jour")
                }}
                className="bg-indigo-600 text-white rounded px-4 py-1.5 text-xs font-semibold hover:bg-indigo-700 h-9 transition-colors"
              >
                Enregistrer
              </button>
            </div>
          </DialogContent>
        </Dialog>
      )}

    </Card>
  )
}
