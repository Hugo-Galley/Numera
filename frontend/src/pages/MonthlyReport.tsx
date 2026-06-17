import { useEffect, useState } from "react"
import { 
  Sparkles, 
  ArrowUpRight, 
  ArrowDownRight, 
  Calendar, 
  TrendingUp, 
  TrendingDown, 
  ShoppingBag,
  Tag,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Printer,
  HeartPulse,
  Banknote,
  PiggyBank,
  Briefcase,
  ShieldCheck,
  ArrowRight,
  Info,
  Wallet,
  Zap
} from "lucide-react"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { useUI } from "@/providers/UIProvider"
import * as LucideIcons from "lucide-react"

const ICON_MAP: Record<string, any> = {
  ...LucideIcons
}

const IconComponent = ({ name, className }: { name?: string, className?: string }) => {
  if (name && (name.startsWith("M") || name.startsWith("<svg") || name.includes("<path"))) {
    return (
      <svg 
        viewBox="0 0 24 24" 
        className={className} 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      >
        {name.startsWith("<svg") ? (
          <g dangerouslySetInnerHTML={{ __html: name.replace(/<svg[^>]*>|<\/svg>/g, '') }} />
        ) : name.includes("<path") ? (
          <g dangerouslySetInnerHTML={{ __html: name }} />
        ) : (
          <path d={name} />
        )}
      </svg>
    )
  }
  const Icon = ICON_MAP[name || "Tag"] || LucideIcons.Tag
  return <Icon className={className} />
}

const FlowSection = ({ title, block, icon: Icon, color, items, isNegative = true }: { 
  title: string, 
  block: MoneyFlowBlock, 
  icon: any, 
  color: string,
  items: MoneyFlowItem[],
  isNegative?: boolean
}) => (
  <div className="group relative pl-8 pb-10 last:pb-0">
    <div className="absolute left-[11px] top-2 bottom-0 w-[2px] bg-slate-100 group-last:hidden"></div>
    <div className={`absolute left-0 top-0 w-6 h-6 rounded-full flex items-center justify-center border-2 border-white shadow-sm z-10 transition-transform group-hover:scale-110 ${color}`}>
      <Icon className="h-3 w-3 text-white" />
    </div>

    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-2">
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-1 block">{title}</span>
          <div className="flex items-baseline gap-3">
            <span className={`text-xl font-black text-slate-900 amount-blur`}>
              {isNegative && block.amount > 0 ? '-' : ''}{formatCurrency(block.amount)}
            </span>
            <span className="text-xs font-bold text-slate-400">
              {block.percentage}%
            </span>
          </div>
        </div>

        <div className="text-right">
          <div className={`text-xs font-bold flex items-center justify-end gap-1 ${
            block.diff_prev_month >= 0 ? 'text-amber-600' : 'text-emerald-600'
          }`}>
            {block.diff_prev_month >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {block.diff_prev_month_pct}%
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {items.slice(0, 4).map((item, i) => (
          <div key={i} className="flex items-center gap-2 px-2.5 py-1 bg-white border border-slate-200 rounded-full shadow-sm">
            <span className="text-[10px] font-bold text-slate-700 truncate max-w-[100px]">{item.name}</span>
            <span className="text-[10px] font-black text-slate-900 amount-blur">{formatCurrency(item.amount)}</span>
          </div>
        ))}
      </div>
    </div>
  </div>
)

interface Insight {
  type: 'anomaly' | 'positive' | 'advice'
  title: string
  description: string
  severity: 'low' | 'medium' | 'high'
  value?: number
}

interface MetricDetail {
  name: string
  score: number
  max_score: number
  value: number
  unit: string
  status: 'good' | 'warning' | 'critical'
}

interface MoneyFlowBlock {
  amount: number
  percentage: number
  diff_prev_month: number
  diff_prev_month_pct: number
}

interface MoneyFlowItem {
  name: string
  amount: number
  category?: string
  is_recurring: boolean
}

interface MoneyFlowData {
  income: number
  fixed_charges: MoneyFlowBlock
  variable_expenses: MoneyFlowBlock
  savings: MoneyFlowBlock
  investments: MoneyFlowBlock
  remainder: MoneyFlowBlock
  top_fixed: MoneyFlowItem[]
  top_variable: MoneyFlowItem[]
  top_savings: MoneyFlowItem[]
  top_investments: MoneyFlowItem[]
}

interface MonthlyReportData {
  month: number
  year: number
  income: number
  expenses: number
  real_expenses: number
  savings: number
  savings_rate: number
  burn_rate: number
  net_worth: number
  net_worth_change: number
  top_categories: Array<{
    name: string
    total: number
    icon?: string
    color?: string
  }>
  top_merchants: Array<{
    merchant: string
    total: number
  }>
  comparison: {
    income_diff: number
    income_diff_pct: number
    expenses_diff: number
    expenses_diff_pct: number
    savings_diff: number
    savings_diff_pct: number
  }
  insights: Insight[]
  health_score: {
    total_score: number
    metrics: MetricDetail[]
  }
  money_flow?: MoneyFlowData
}

const MONTHS = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

export default function IntelligentReport() {
  const { isPrivacyMode } = useUI()
  const [data, setData] = useState<MonthlyReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [date, setDate] = useState(() => {
    const d = new Date()
    return { month: d.getMonth() + 1, year: d.getFullYear() }
  })

  useEffect(() => {
    async function fetchReport() {
      setLoading(true)
      try {
        const report = await api.get<MonthlyReportData>(`/analytics/monthly-report?month=${date.month}&year=${date.year}`)
        setData(report)
      } catch (err) {
        console.error("Error fetching monthly report:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchReport()
  }, [date])

  const changeMonth = (delta: number) => {
    setDate(prev => {
      let newMonth = prev.month + delta
      let newYear = prev.year
      if (newMonth > 12) {
        newMonth = 1
        newYear++
      } else if (newMonth < 1) {
        newMonth = 12
        newYear--
      }
      return { month: newMonth, year: newYear }
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
      </div>
    )
  }

  if (!data) return (
    <div className="p-8 text-center bg-white rounded-xl border border-dashed border-slate-200">
      <p className="text-slate-500 font-medium">Erreur lors du chargement du bilan. Veuillez réessayer.</p>
      <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>Actualiser</Button>
    </div>
  )

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col gap-4">
        <div className="no-print self-end">
          <Button 
            variant="outline"
            size="sm"
            className="gap-2 rounded-lg font-medium text-slate-600 hover:text-slate-900 bg-white shadow-sm border-slate-200"
            onClick={() => window.print()}
          >
            <Printer className="h-4 w-4" />
            Exporter en PDF
          </Button>
        </div>

        {/* Header & Month Selector */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-slate-900 flex items-center gap-3">
              <Sparkles className="h-8 w-8 text-amber-500" />
              Bilan Mensuel Intelligent & Analyse de flux
            </h1>
            <p className="text-slate-500 font-medium">Analyse et synthèse de votre activité financière.</p>
          </div>
        
        <div className="flex items-center bg-white rounded-xl p-1 shadow-sm border border-slate-200">
          <Button variant="ghost" size="icon" onClick={() => changeMonth(-1)} className="rounded-lg h-9 w-9">
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div className="px-4 font-bold text-slate-900 min-w-[140px] text-center">
            {(data.month && data.month >= 1 && data.month <= 12) ? MONTHS[data.month - 1] : "Mois Inconnu"} {data.year}
          </div>
          <Button variant="ghost" size="icon" onClick={() => changeMonth(1)} className="rounded-lg h-9 w-9">
            <ChevronRight className="h-5 w-5" />
          </Button>
        </div>
      </div>
      </div>

      <Tabs defaultValue="synthesis" className="w-full space-y-8">
        <div className="flex justify-center md:justify-start">
          <TabsList className="bg-slate-50/50 border border-slate-100 p-1 rounded-xl inline-flex w-max mb-2">
            <TabsTrigger value="synthesis" className="rounded-lg whitespace-nowrap gap-2">
              <Sparkles className="h-3.5 w-3.5 text-amber-500" />
              Vue d'Ensemble
            </TabsTrigger>
            <TabsTrigger value="flow" className="rounded-lg whitespace-nowrap gap-2">
              <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
              Flux de Trésorerie
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="synthesis" className="space-y-8 focus-visible:outline-none mt-0">
          {/* Main Score & Summary Card */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 border-none shadow-md overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 text-white">
          <CardContent className="p-8">
            <div className="flex flex-col md:flex-row gap-8 items-center">
              {/* Health Score Gauge */}
              <div className="relative flex-shrink-0">
                <svg className="w-48 h-48 transform -rotate-90">
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="transparent"
                    className="text-slate-700"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="transparent"
                    strokeDasharray={552.92}
                    strokeDashoffset={552.92 - (552.92 * (data.health_score?.total_score || 0)) / 100}
                    className={
                      (data.health_score?.total_score || 0) > 75 ? "text-emerald-400" : 
                      (data.health_score?.total_score || 0) > 50 ? "text-amber-400" : "text-rose-400"
                    }
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-5xl font-black leading-none">{Math.round(data.health_score?.total_score || 0)}</span>
                  <span className="text-xs font-bold uppercase tracking-wider opacity-60">Score Santé</span>
                </div>
              </div>

              {/* Summary Text */}
              <div className="flex-1 space-y-4">
                <div className="space-y-1">
                  <h3 className="text-2xl font-bold">
                    {(data.health_score?.total_score || 0) > 75 ? "Excellent mois !" : 
                     (data.health_score?.total_score || 0) > 50 ? "Mois équilibré" : "Attention requise"}
                  </h3>
                  <p className="text-slate-400 leading-relaxed">
                    Ce mois-ci, vous avez généré <span className="text-white font-bold">{formatCurrency(data.income)}</span> de revenus 
                    et dépensé <span className="text-white font-bold">{formatCurrency(data.real_expenses)}</span> en frais de vie.
                    Votre taux d'épargne est de <span className="text-white font-bold">{data.savings_rate}%</span>.
                  </p>
                </div>
                
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="bg-white/10 rounded-xl p-3">
                    <div className="text-xs font-bold text-slate-400 uppercase mb-1">Variation Patrimoine</div>
                    <div className={`text-lg font-black flex items-center gap-1 ${data.net_worth_change >= 0 ? 'text-emerald-400' : 'text-rose-400'} amount-blur`}>
                      {data.net_worth_change >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                      {formatCurrency(data.net_worth_change)}
                    </div>
                  </div>
                  <div className="bg-white/10 rounded-xl p-3">
                    <div className="text-xs font-bold text-slate-400 uppercase mb-1">Burn Rate</div>
                    <div className="text-lg font-black text-white amount-blur">
                      {formatCurrency(data.burn_rate)} <span className="text-xs font-normal opacity-60">/ jour</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Comparison Card */}
        <Card className="border-none shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold">Évolution vs Mois Dernier</CardTitle>
            <CardDescription>Comparaison avec {MONTHS[(data.month - 2 + 12) % 12]}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-600 text-sm font-medium">
                  <Banknote className="h-4 w-4" /> Revenus
                </div>
                <div className={`text-sm font-bold flex items-center ${data.comparison?.income_diff >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {data.comparison?.income_diff >= 0 ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                  {Math.abs(data.comparison?.income_diff_pct || 0)}%
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-600 text-sm font-medium">
                  <ShoppingBag className="h-4 w-4" /> Dépenses
                </div>
                <div className={`text-sm font-bold flex items-center ${data.comparison?.expenses_diff <= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {data.comparison?.expenses_diff > 0 ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                  {Math.abs(data.comparison?.expenses_diff_pct || 0)}%
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-600 text-sm font-medium">
                  <PiggyBank className="h-4 w-4" /> Épargne
                </div>
                <div className={`text-sm font-bold flex items-center ${data.comparison?.savings_diff >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {data.comparison?.savings_diff >= 0 ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                  {Math.abs(data.comparison?.savings_diff_pct || 0)}%
                </div>
              </div>
            </div>
            
            <div className="pt-2 border-t space-y-4">
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-bold uppercase text-slate-400">
                  <span>Score par métrique</span>
                  <span>100%</span>
                </div>
                <div className="space-y-3 pt-1">
                  {data.health_score?.metrics?.map((m, i) => (
                    <div key={i} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-slate-700">{m.name}</span>
                        <span className="text-slate-900 font-bold">{Math.round((m.score / m.max_score) * 100)}%</span>
                      </div>
                      <Progress 
                        value={(m.score / m.max_score) * 100} 
                        className="h-1.5" 
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Insights & Anomalies */}
        <div className="space-y-4">
          <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
            <HeartPulse className="h-6 w-6 text-rose-500" />
            Signaux du mois
          </h2>
          <div className="space-y-4">
            {data.insights?.map((insight, i) => (
              <Card key={i} className={`border-none shadow-sm border-l-4 ${
                insight.type === 'anomaly' ? 'border-l-amber-500' : 
                insight.type === 'positive' ? 'border-l-emerald-500' : 'border-l-blue-500'
              }`}>
                <CardContent className="p-4 flex gap-4 items-start">
                  <div className={`p-2 rounded-lg ${
                    insight.type === 'anomaly' ? 'bg-amber-100 text-amber-600' : 
                    insight.type === 'positive' ? 'bg-emerald-100 text-emerald-600' : 'bg-blue-100 text-blue-600'
                  }`}>
                    {insight.type === 'anomaly' ? <AlertTriangle className="h-5 w-5" /> : 
                     insight.type === 'positive' ? <Sparkles className="h-5 w-5" /> : <TrendingUp className="h-5 w-5" />}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-bold text-slate-900">{insight.title}</h4>
                    <p className="text-sm text-slate-600 mt-0.5">{insight.description}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
            {(!data.insights || data.insights.length === 0) && (
              <div className="bg-slate-50 border border-dashed border-slate-200 rounded-xl p-8 text-center text-slate-400 font-medium">
                Aucun signal particulier détecté ce mois-ci.
              </div>
            )}
          </div>
        </div>

        {/* Top Spending */}
        <div className="space-y-4">
          <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
            <Tag className="h-6 w-6 text-blue-500" />
            Top Dépenses
          </h2>
          <Card className="border-none shadow-md overflow-hidden bg-white">
            <CardHeader className="pb-3 border-b bg-slate-50/50">
              <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-500">Par Catégorie</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="grid grid-cols-1 divide-y divide-slate-100">
                {data.top_categories?.map((cat, i) => (
                  <div key={i} className="p-4 flex items-center hover:bg-slate-50/80 transition-colors group gap-4">
                    {/* Fixed Size Icon Container */}
                    <div 
                      className="w-12 h-12 flex-shrink-0 rounded-2xl flex items-center justify-center shadow-sm border border-white transition-transform group-hover:scale-105 overflow-hidden" 
                      style={{ backgroundColor: `${cat.color}15`, color: cat.color }}
                    >
                      <IconComponent name={cat.icon} className="w-6 h-6" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-slate-900 truncate text-base">{cat.name}</span>
                        <span className="font-black text-slate-900 amount-blur text-lg whitespace-nowrap">
                          {formatCurrency(cat.total)}
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full mt-1.5 overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-1000" 
                          style={{ 
                            width: `${Math.min(100, (cat.total / (data.top_categories?.[0]?.total || 1)) * 100)}%`,
                            backgroundColor: cat.color 
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
                {(!data.top_categories || data.top_categories.length === 0) && (
                  <div className="p-8 text-center text-slate-400 italic">Aucune donnée de catégorie.</div>
                )}
              </div>
              
              <div className="bg-slate-50/50 p-6 border-t border-slate-100">
                <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <ShoppingBag className="h-3.5 w-3.5" />
                  Marchands Favoris
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {data.top_merchants?.map((m, i) => (
                    <div 
                      key={i} 
                      className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md transition-all amount-blur group"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0 text-slate-500 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                          <ShoppingBag className="w-4 h-4" />
                        </div>
                        <span className="font-bold text-slate-700 truncate text-sm">{m.merchant}</span>
                      </div>
                      <span className="font-black text-slate-900 text-sm whitespace-nowrap ml-2">
                        {formatCurrency(m.total)}
                      </span>
                    </div>
                  ))}
                  {(!data.top_merchants || data.top_merchants.length === 0) && (
                    <div className="col-span-full text-slate-400 text-sm italic py-2">Aucun marchand identifié.</div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
      
        </TabsContent>

        <TabsContent value="flow" className="focus-visible:outline-none mt-0">
          {/* Money Flow Analysis Section */}
          {data.money_flow ? (
            <div className="space-y-6">
              <h2 className="text-2xl font-black text-slate-900 flex items-center gap-2">
                <TrendingUp className="h-7 w-7 text-emerald-500" />
                Analyse des Flux Réels
              </h2>
          
          <Card className="border-none shadow-md overflow-hidden bg-white">
            <CardContent className="p-8">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                {/* Left Column: Narrative Flow */}
                <div className="space-y-10">
                  {/* Entry Node */}
                  <div className="relative">
                    <div className="absolute left-[11px] top-6 bottom-0 w-[2px] bg-slate-100"></div>
                    <div className="flex items-start gap-8">
                      <div className="w-6 h-6 rounded-full bg-emerald-500 border-4 border-white shadow-md z-10 flex-shrink-0 flex items-center justify-center">
                        <LucideIcons.Plus className="h-3 w-3 text-white" />
                      </div>
                      <div className="flex-1 -mt-1">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-1 block">Entrées Réelles</span>
                        <div className="text-3xl font-black text-slate-900 amount-blur">
                          {formatCurrency(data.money_flow.income)}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Flow Steps */}
                  <div className="space-y-0">
                    <FlowSection 
                      title="Charges Fixes" 
                      block={data.money_flow.fixed_charges} 
                      icon={ShieldCheck} 
                      color="bg-slate-900"
                      items={data.money_flow.top_fixed}
                    />
                    <FlowSection 
                      title="Dépenses Variables" 
                      block={data.money_flow.variable_expenses} 
                      icon={ShoppingBag} 
                      color="bg-rose-500"
                      items={data.money_flow.top_variable}
                    />
                    <FlowSection 
                      title="Épargne" 
                      block={data.money_flow.savings} 
                      icon={PiggyBank} 
                      color="bg-amber-500"
                      items={data.money_flow.top_savings}
                    />
                    <FlowSection 
                      title="Investissements" 
                      block={data.money_flow.investments} 
                      icon={Briefcase} 
                      color="bg-blue-600"
                      items={data.money_flow.top_investments}
                    />
                  </div>

                  {/* Exit Node */}
                  <div className="relative">
                    <div className="flex items-start gap-8">
                      <div className="w-6 h-6 rounded-full bg-slate-900 border-4 border-white shadow-lg z-10 flex-shrink-0 flex items-center justify-center">
                        <ArrowRight className="h-3 w-3 text-white" />
                      </div>
                      <div className="flex-1 -mt-1 bg-slate-50 rounded-2xl p-4 border border-slate-100 shadow-sm">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] block">Solde Final</span>
                        <div className={`text-2xl font-black text-slate-900 amount-blur ${data.money_flow.remainder.amount < 0 ? 'text-rose-600' : ''}`}>
                          {formatCurrency(data.money_flow.remainder.amount)}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Column: Key Metrics & Chart */}
                <div className="space-y-8 flex flex-col justify-center">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Rétention</div>
                      <div className="text-2xl font-black text-slate-900">{data.money_flow.remainder.percentage}%</div>
                      <p className="text-[10px] text-slate-500 mt-1">Revenus restants après flux.</p>
                    </div>
                    <div className="p-4 bg-slate-900 text-white rounded-2xl">
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Épargne Réelle</div>
                      <div className="text-2xl font-black">
                        {Math.round(((data.money_flow.savings.amount + data.money_flow.investments.amount + (data.money_flow.remainder.amount > 0 ? data.money_flow.remainder.amount : 0)) / data.money_flow.income) * 100)}%
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">Épargne + Invest + Reste.</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      <Zap className="h-3 w-3 text-amber-500" /> Répartition de l'Allocation
                    </div>
                    <div className="flex h-4 rounded-full overflow-hidden bg-slate-100 border border-slate-200">
                      <div className="bg-slate-900" style={{ width: `${data.money_flow.fixed_charges.percentage}%` }} title="Fixe"></div>
                      <div className="bg-rose-500" style={{ width: `${data.money_flow.variable_expenses.percentage}%` }} title="Variable"></div>
                      <div className="bg-amber-500" style={{ width: `${data.money_flow.savings.percentage}%` }} title="Épargne"></div>
                      <div className="bg-blue-600" style={{ width: `${data.money_flow.investments.percentage}%` }} title="Invest."></div>
                    </div>
                    <div className="flex flex-wrap gap-x-6 gap-y-2 pt-1">
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-600"><div className="w-2 h-2 rounded-full bg-slate-900"></div> Fixe</div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-600"><div className="w-2 h-2 rounded-full bg-rose-500"></div> Variable</div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-600"><div className="w-2 h-2 rounded-full bg-amber-500"></div> Épargne</div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-600"><div className="w-2 h-2 rounded-full bg-blue-600"></div> Invest.</div>
                    </div>
                  </div>

                  <div className="p-6 bg-blue-50/50 rounded-2xl border border-blue-100">
                    <div className="flex items-start gap-3">
                      <Info className="h-5 w-5 text-blue-500 mt-0.5" />
                      <p className="text-sm text-slate-600 leading-relaxed font-medium">
                        {data.money_flow.remainder.amount > 0 ? (
                          <>Vous avez conservé <span className="font-bold text-slate-900">{formatCurrency(data.money_flow.remainder.amount)}</span> après toutes vos dépenses et placements. Ce montant vient renforcer votre trésorerie disponible.</>
                        ) : (
                          <>Vos sorties ont dépassé vos entrées de <span className="font-bold text-rose-600">{formatCurrency(Math.abs(data.money_flow.remainder.amount))}</span>. Ce déficit a été couvert par vos réserves de cash existantes.</>
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
            </div>
          ) : (
            <div className="p-8 text-center bg-white rounded-xl border border-dashed border-slate-200">
              <p className="text-slate-500 font-medium">Aucune donnée de flux disponible pour ce mois.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>

      <style>{`
        @media print {
          @page {
            size: A4;
            margin: 15mm;
          }
          
          body {
            background: white !important;
            color: black !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }

          .no-print, nav, header, button, .sidebar, aside, .bottom-actions {
            display: none !important;
          }

          .space-y-8 {
            margin: 0 !important;
            padding: 0 !important;
          }

          .shadow-md, .shadow-sm, .shadow-lg {
            box-shadow: none !important;
            border: 1px solid #e2e8f0 !important;
          }

          /* Force background colors in print */
          .bg-gradient-to-br {
            background: #1e293b !important;
            color: white !important;
          }
          
          .bg-slate-900 { background-color: #0f172a !important; }
          .bg-slate-50 { background-color: #f8fafc !important; }
          .bg-emerald-400 { color: #34d399 !important; }
          .bg-amber-400 { color: #fbbf24 !important; }
          .bg-rose-400 { color: #f87171 !important; }

          /* Layout fixes for print */
          .grid {
            display: grid !important;
            gap: 1.5rem !important;
          }
          
          .lg\\:grid-cols-3 { grid-template-cols: repeat(3, minmax(0, 1fr)) !important; }
          .lg\\:grid-cols-2 { grid-template-cols: repeat(2, minmax(0, 1fr)) !important; }
          .lg\\:col-span-2 { grid-column: span 2 / span 2 !important; }
          
          /* Prevent items from breaking across pages */
          .card, .Card {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
          }

          /* Scale down slightly to ensure fit */
          .space-y-8 {
            zoom: 0.9;
          }
          
          /* Ensure charts and gauges are visible */
          svg {
            display: block !important;
          }
          
          /* Reveal blurred amounts in export */
          .amount-blur {
            filter: none !important;
          }
        }
      `}</style>
    </div>
  )
}
