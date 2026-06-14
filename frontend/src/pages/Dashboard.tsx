import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Calendar,
  CreditCard,
  PieChart as PieChartIcon,
  BarChart3,
  TrendingUp,
  LineChart as LineChartIcon,
  Users,
  Briefcase,
  History as HistoryIcon,
  Layers,
  Sparkles,
  HeartPulse,
  Tag,
  Coffee,
  ShoppingBag,
  Utensils,
  Car,
  Home,
  Heart,
  Zap,
  Music,
  Smartphone,
  Plane,
  Gift,
  Banknote,
  Trophy,
  User,
  Film,
  Dumbbell,
  AlertTriangle,
  Search,
  Settings as SettingsIcon,
  Plus,
  Trash2,
  Pencil,
  Repeat,
  ChevronLeft,
  ChevronRight,
  Download,
  Database,
  Airplay,
  AlarmClock,
  Archive,
  Award,
  Backpack,
  Bath,
  Beer,
  Bell,
  Bike,
  Book,
  Box,
  Camera,
  Clapperboard,
  Cloud,
  Compass,
  Cookie,
  Cpu,
  Dice5,
  Dog,
  Droplet,
  Egg,
  Eye,
  Fan,
  Feather,
  Fish,
  Flag,
  Flashlight,
  FlaskConical,
  Flower,
  Footprints,
  Fuel,
  Gamepad2,
  GlassWater,
  Globe,
  Grape,
  Hammer,
  IceCream,
  Key,
  Laptop,
  Library,
  Lightbulb,
  Locate,
  Lock,
  Map,
  Mic,
  Monitor,
  Moon,
  Mountain,
  Mouse,
  Network,
  Newspaper,
  Nut,
  Package,
  Paintbrush,
  Palmtree,
  Paperclip,
  PawPrint,
  Phone,
  Pizza,
  Plug,
  Printer,
  Puzzle,
  Radio,
  Receipt,
  Recycle,
  Rocket,
  Route,
  Rss,
  Sailboat,
  Scissors,
  ScreenShare,
  Shield,
  Ship,
  Shirt,
  ShowerHead,
  Skull,
  Smile,
  Snowflake,
  Speaker,
  Sprout,
  Stamp,
  Star,
  Stethoscope,
  Sun,
  Sunrise,
  Sunset,
  Tablet,
  Target,
  Tent,
  Terminal,
  Thermometer,
  Ticket,
  Timer,
  Train,
  Trash,
  TreeDeciduous,
  TreePine,
  Trees,
  Tv,
  Umbrella,
  UtilityPole,
  Variable,
  Video,
  Voicemail,
  Volume2,
  Watch,
  Waves,
  Webcam,
  Weight,
  Wifi,
  Wind,
  Wine,
  Wrench
} from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
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
  CartesianGrid,
  LineChart,
  Line,
  AreaChart,
  Area,
  Legend,
  ReferenceLine,
} from "recharts"
import { api } from "@/lib/api"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { SankeyFlow } from "@/components/analytics/SankeyFlow"
import { format } from "date-fns"
import { fr } from "date-fns/locale"

const COLORS = ["#3b82f6", "#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#f59e0b", "#64748b"]

const ICON_MAP: Record<string, any> = {
  Coffee, ShoppingBag, Utensils, Car, Home, Heart, Zap, Music, Smartphone, Plane, Gift, 
  Briefcase, CreditCard, Wallet, Banknote, 
  Trophy, Activity, User, Film, Dumbbell, Tag,
  Airplay, AlarmClock, Archive, Award, Backpack, Bath, Beer, Bell, Bike, Book, Box, Camera,
  Clapperboard, Cloud, Compass, Cookie, Cpu, Dice5, Dog, Droplet, Egg, Eye, Fan, Feather,
  Fish, Flag, Flashlight, FlaskConical, Flower, Footprints, Fuel, Gamepad2, GlassWater,
  Globe, Grape, Hammer, IceCream, Key, Laptop, Library, Lightbulb, Locate, Lock,
  Map, Mic, Monitor, Moon, Mountain, Mouse, Network, Newspaper, Nut, Package, Paintbrush,
  Palmtree, Paperclip, PawPrint, Phone, Pizza, Plug, Printer, Puzzle, Radio, Receipt,
  Recycle, Rocket, Route, Rss, Sailboat, Scissors, ScreenShare, Search, Settings: SettingsIcon,
  Shield, Ship, Shirt, ShowerHead, Skull, Smile, Snowflake, Speaker, Sprout, Stamp, Star,
  Stethoscope, Sun, Sunrise, Sunset, Tablet, Target, Tent, Terminal, Thermometer, Ticket,
  Timer, Train, Trash, TreeDeciduous, TreePine, Trees, Tv, Umbrella, UtilityPole, Variable,
  Video, Voicemail, Volume2, Watch, Waves, Webcam, Weight, Wifi, Wind, Wine, Wrench
}

const IconComponent = ({ name, className }: { name?: string | null, className?: string }) => {
  if (!name) return <Tag className={className} />
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
  const Icon = ICON_MAP[name || "Tag"] || Tag
  return <Icon className={className} />
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [accounts, setAccounts] = useState<any[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>("all")
  const [analytics, setAnalytics] = useState<any>(null)
  const [expensesByCategory, setExpensesByCategory] = useState<any[]>([])
  const [kpiHistory, setKpiHistory] = useState<any[]>([])
  const [topMerchants, setTopMerchants] = useState<any[]>([])
  const [subscriptions, setSubscriptions] = useState<any>(null)
  const [salarySeries, setSalarySeries] = useState<any[]>([])
  const [investments, setInvestments] = useState<any>(null)
  const [allocation, setAllocation] = useState<any>(null)
  const [burnRateSeries, setBurnRateSeries] = useState<any[]>([])
  const [budgetAlerts, setBudgetAlerts] = useState<any[]>([])
  const [insights, setInsights] = useState<any>(null)
  const [sankeyData, setSankeyData] = useState<any>(null)
  const [projection, setProjection] = useState<any>(null)
  const [tagTotals, setTagTotals] = useState<any[]>([])

  useEffect(() => {
    async function init() {
      try {
        const accs = await api.get<any[]>("/accounts")
        if (accs && Array.isArray(accs)) {
          setAccounts(accs)
          const defaultAcc = accs.find(a => a.type === "courant" && a.active)
          if (defaultAcc) {
            setSelectedAccountId(String(defaultAcc.id))
          }
        } else {
          setAccounts([])
        }
      } catch (error) {
        console.error("Failed to load accounts", error)
      }
    }
    init()
  }, [])

  useEffect(() => {
    async function loadData() {
      const accId = selectedAccountId === "all" ? null : selectedAccountId
      const accParam = accId ? `&account_id=${accId}` : ""

      // Individual loaders with error handling to avoid breaking the whole dashboard
      const safeLoad = async (url: string, setter: (data: any) => void) => {
        try {
          // console.log(`Fetching ${url}...`)
          const data = await api.get<any>(url)
          setter(data)
        } catch (e: any) {
          console.error(`Error loading ${url}:`, e)
          // Specifically show if it's the "An error occurred" generic one
          if (e.message === "An error occurred") {
             console.warn(`Endpoint ${url} returned a generic 500 error. Check backend logs.`)
          }
        }
      }

      safeLoad(`/analytics/budget?month=${month}&year=${year}${accParam}`, setAnalytics)
      safeLoad(`/analytics/expenses-by-category?month=${month}&year=${year}${accParam}`, (d) => setExpensesByCategory(d?.items || []))
      safeLoad(`/analytics/kpi-history?months_count=6${accParam}`, setKpiHistory)
      safeLoad(`/analytics/top-merchants?month=${month}&year=${year}${accParam}`, (d) => setTopMerchants(d?.items || []))
      safeLoad(`/analytics/subscriptions?month=${month}&year=${year}${accParam}`, setSubscriptions)
      safeLoad(`/analytics/timeseries?year=${year}${accParam}`, (d) => {
        setSalarySeries(d?.salary_series || [])
        setBurnRateSeries(d?.monthly_flows || [])
      })
      safeLoad(`/analytics/investments?month=${month}&year=${year}${accParam}`, setInvestments)
      safeLoad(`/analytics/investments-allocation${accId ? `?account_id=${accId}` : ""}`, setAllocation)
      safeLoad(`/analytics/budget-alerts?month=${month}&year=${year}${accParam}`, setBudgetAlerts)
      safeLoad(`/analytics/insights?month=${month}&year=${year}${accParam}`, setInsights)
      safeLoad(`/analytics/sankey?month=${month}&year=${year}${accParam}`, setSankeyData)
      safeLoad(`/analytics/cashflow-projection?days=60${accId ? `&account_id=${accId}` : ""}`, setProjection)
      safeLoad(`/analytics/tags?month=${month}&year=${year}${accParam}`, setTagTotals)
    }
    loadData()
  }, [month, year, selectedAccountId])

  const onAllocationClick = useCallback((_: any, index: number) => {
    const item = allocation?.items?.[index]
    if (item && item.account_id) {
      navigate(`/accounts/${item.account_id}`)
    }
  }, [allocation, navigate])

  const onInvestmentBarClick = useCallback((data: any) => {
    if (data && data.account_id) {
      navigate(`/accounts/${data.account_id}`)
    }
  }, [navigate])

  const formatCurrency = (value: number | null | undefined, currencyCode: string = "EUR") => {
    const safeValue = value || 0
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: currencyCode }).format(safeValue)
  }

  const safeFormat = (dateStr: string | null | undefined, formatStr: string) => {
    if (!dateStr) return "-"
    try {
      const d = new Date(dateStr)
      if (isNaN(d.getTime())) return "-"
      return format(d, formatStr, { locale: fr })
    } catch (e) {
      return "-"
    }
  }

  const selectedAccount = accounts.find(a => String(a.id) === selectedAccountId)
  const displayCurrency = selectedAccount?.currency || "EUR"

  const alertsOver = budgetAlerts.filter(a => (a.monthly_ratio != null && a.monthly_ratio >= 1) || (a.annual_ratio != null && a.annual_ratio >= 1))

  const months = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
  ]

  const Sparkline = ({ data, dataKey, color }: { data: any[], dataKey: string, color: string }) => (
    <div className="h-10 w-full mt-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
          <Area 
            type="monotone" 
            dataKey={dataKey} 
            stroke={color} 
            fill={color} 
            fillOpacity={0.1} 
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )

  return (
    <div className="space-y-10 pb-10">
      {/* Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900">Tableau de bord</h1>
          <p className="text-slate-500 mt-1">Toutes vos analyses financières en un coup d'œil.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 md:gap-3 bg-white p-1.5 md:p-2 rounded-xl border shadow-sm w-fit">
          <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
            <SelectTrigger className="w-[140px] md:w-[180px] border-none shadow-none focus:ring-0 font-medium h-8 md:h-10">
              <SelectValue placeholder="Comptes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les comptes</SelectItem>
              {accounts.map((acc) => (
                <SelectItem key={acc.id} value={String(acc.id)}>{acc.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Separator orientation="vertical" className="h-6 hidden md:block" />
          <Select value={String(month)} onValueChange={(v: string) => setMonth(Number(v))}>
            <SelectTrigger className="w-[110px] md:w-[130px] border-none shadow-none focus:ring-0 h-8 md:h-10">
              <SelectValue placeholder="Mois" />
            </SelectTrigger>
            <SelectContent>
              {months.map((m, i) => (
                <SelectItem key={i + 1} value={String(i + 1)}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Separator orientation="vertical" className="h-6 hidden md:block" />
          <Select value={String(year)} onValueChange={(v: string) => setYear(Number(v))}>
            <SelectTrigger className="w-[80px] md:w-[100px] border-none shadow-none focus:ring-0 h-8 md:h-10">
              <SelectValue placeholder="Année" />
            </SelectTrigger>
            <SelectContent>
              {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i).map((y) => (
                <SelectItem key={y} value={String(y)}>{y}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Main KPI Grid */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="shadow-sm border-slate-100 hover:border-emerald-200 transition-colors cursor-pointer group">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardDescription className="font-medium group-hover:text-emerald-600 transition-colors">
              {selectedAccountId === "all" ? "Revenus Mensuels" : "Entrées d'argent"}
            </CardDescription>
            <div className="h-8 w-8 bg-emerald-50 rounded-full flex items-center justify-center group-hover:bg-emerald-100 transition-colors">
              <ArrowUpRight className="h-4 w-4 text-emerald-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold">
              <span className="amount-blur">{formatCurrency(analytics?.revenus_totaux || 0, displayCurrency)}</span>
            </CardTitle>
            <Sparkline data={kpiHistory} dataKey="revenus" color="#10b981" />
            <p className="text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-100 hover:border-rose-200 transition-colors cursor-pointer group">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardDescription className="font-medium group-hover:text-rose-600 transition-colors">
              {selectedAccountId === "all" ? "Dépenses Mensuelles" : "Sorties d'argent"}
            </CardDescription>
            <div className="h-8 w-8 bg-rose-50 rounded-full flex items-center justify-center group-hover:bg-rose-100 transition-colors">
              <ArrowDownRight className="h-4 w-4 text-rose-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold">
              <span className="amount-blur">{formatCurrency(analytics?.depenses_totales || 0, displayCurrency)}</span>
            </CardTitle>
            <Sparkline data={kpiHistory} dataKey="depenses" color="#f43f5e" />
            <p className="text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-100 hover:border-blue-200 transition-colors cursor-pointer group">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardDescription className="font-medium group-hover:text-blue-600 transition-colors">
              {selectedAccountId === "all" ? "Épargne Réalisée" : "Solde Actuel"}
            </CardDescription>
            <div className="h-8 w-8 bg-blue-50 rounded-full flex items-center justify-center group-hover:bg-blue-100 transition-colors">
              <Wallet className="h-4 w-4 text-blue-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold">
              <span className="amount-blur">
                {formatCurrency(selectedAccountId === "all" ? analytics?.revenus_apres_depenses : analytics?.solde_actuel, displayCurrency)}
              </span>
            </CardTitle>
            <Sparkline data={kpiHistory} dataKey="epargne_flow" color="#3b82f6" />
            <p className="text-[10px] text-slate-400 mt-2 uppercase tracking-wider font-bold">Tendance 6 mois</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-100 hover:border-slate-300 transition-colors cursor-pointer group">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardDescription className="font-medium group-hover:text-slate-900 transition-colors">Patrimoine Net</CardDescription>
            <div className="h-8 w-8 bg-slate-50 rounded-full flex items-center justify-center group-hover:bg-slate-200 transition-colors">
              <Activity className="h-4 w-4 text-slate-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold">
              <span className="amount-blur">{formatCurrency(analytics?.patrimoine_net_total || 0, "EUR")}</span>
            </CardTitle>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="outline" className="text-[10px] font-bold py-0 h-4 border-slate-200 text-slate-500">Global</Badge>
              <span className="text-[10px] text-slate-400">Tous les comptes</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-8">
        <div className="overflow-x-auto pb-2 [ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <TabsList className="bg-slate-100 p-1 rounded-xl inline-flex w-auto min-w-full">
            <TabsTrigger value="overview" className="rounded-lg whitespace-nowrap">Aperçu Général</TabsTrigger>
            
            <TabsTrigger value="insights" className="rounded-lg whitespace-nowrap">Insights</TabsTrigger>
            <TabsTrigger value="merchants" className="rounded-lg whitespace-nowrap">Top Commerçants</TabsTrigger>
            <TabsTrigger value="budgets" className="rounded-lg whitespace-nowrap">Budgets</TabsTrigger>
            <TabsTrigger value="subscriptions" className="rounded-lg whitespace-nowrap">Abonnements</TabsTrigger>
            <TabsTrigger value="investments" className="rounded-lg whitespace-nowrap">Investissements</TabsTrigger>
            <TabsTrigger value="history" className="rounded-lg whitespace-nowrap">Évolutions</TabsTrigger>
            <TabsTrigger value="projections" className="rounded-lg whitespace-nowrap">Projections</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="projections" className="space-y-8">
          <div className="grid gap-6 md:grid-cols-3">
            <Card className="shadow-sm border-slate-100">
              <CardHeader className="pb-2">
                <CardDescription className="font-medium text-slate-500">Solde Projeté (60j)</CardDescription>
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
                  {formatCurrency(projection?.projected_balance || 0, displayCurrency)}
                </CardTitle>
                <div className="flex items-center gap-1.5 mt-1">
                   <TrendingUp className={`h-3.5 w-3.5 ${((projection?.projected_balance || 0) >= (projection?.current_balance || 0)) ? 'text-emerald-500' : 'text-rose-500'}`} />
                   <span className={`text-xs font-bold ${((projection?.projected_balance || 0) >= (projection?.current_balance || 0)) ? 'text-emerald-600' : 'text-rose-600'}`}>
                     {((projection?.projected_balance || 0) - (projection?.current_balance || 0) > 0 ? "+" : "")}
                     {formatCurrency((projection?.projected_balance || 0) - (projection?.current_balance || 0), displayCurrency)}
                   </span>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-sm border-slate-100">
              <CardHeader className="pb-2">
                <CardDescription className="font-medium text-slate-500">Point le plus bas</CardDescription>
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
                  {formatCurrency(projection?.low_point || 0, displayCurrency)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-1 uppercase font-bold tracking-tight">
                  Prévu le {projection?.low_point_date ? format(new Date(projection.low_point_date), "d MMMM", { locale: fr }) : "-"}
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-sm border-slate-100">
              <CardHeader className="pb-2">
                <CardDescription className="font-medium text-slate-500">Flux récurrents attendus</CardDescription>
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900">
                  {projection?.events?.length || 0}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-1 uppercase font-bold tracking-tight">Prochains 60 jours</p>
              </CardContent>
            </Card>
          </div>

          <Card className="shadow-sm border-slate-100 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b pb-4">
              <CardTitle className="text-lg">Évolution du Solde Projeté</CardTitle>
              <CardDescription>Projection basée sur vos revenus et dépenses récurrentes sur les 2 prochains mois.</CardDescription>
            </CardHeader>
            <CardContent className="p-0 sm:p-6 h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={projection?.points || []} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
                  <defs>
                    <linearGradient id="colorProj" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 10, fill: '#64748b' }} 
                    tickFormatter={(v) => safeFormat(v, "d MMM")}
                    minTickGap={30}
                  />
                  <YAxis 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 12, fill: '#64748b' }} 
                    tickFormatter={(v) => `${Math.round(v)}€`}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} 
                    labelFormatter={(v) => format(new Date(v), "EEEE d MMMM", { locale: fr })}
                    formatter={(v: number) => [formatCurrency(v, displayCurrency), "Solde estimé"]}
                  />
                  <Area type="monotone" dataKey="balance" name="Solde" stroke="#3b82f6" fill="url(#colorProj)" strokeWidth={4} />
                  <ReferenceLine y={0} stroke="#f43f5e" strokeDasharray="3 3" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid gap-8 lg:grid-cols-2">
             <Card className="shadow-sm border-slate-100">
               <CardHeader>
                 <CardTitle className="text-lg">Prochains flux</CardTitle>
                 <CardDescription>Événements prévus dans les 30 prochains jours.</CardDescription>
               </CardHeader>
               <CardContent className="p-0">
                 <div className="divide-y">
                   {projection?.events?.slice(0, 10).map((ev: any, i: number) => (
                     <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                       <div className="flex items-center gap-3">
                         <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${ev.is_income ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                           {ev.is_income ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                         </div>
                         <div>
                           <p className="text-sm font-bold text-slate-900">{ev.name}</p>
                           <p className="text-[10px] text-slate-500 font-medium uppercase">{format(new Date(ev.date), "d MMMM", { locale: fr })}</p>
                         </div>
                       </div>
                       <span className={`text-sm font-black amount-blur ${ev.is_income ? 'text-emerald-600' : 'text-slate-900'}`}>
                         {ev.is_income ? '+' : '-'}{formatCurrency(ev.amount, displayCurrency)}
                       </span>
                     </div>
                   ))}
                 </div>
               </CardContent>
             </Card>

             <div className="space-y-6">
                <Card className="shadow-sm border-blue-100 bg-blue-50/20">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-blue-500" />
                      Analyse de trésorerie
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-slate-600 leading-relaxed">
                      Votre solde devrait rester **positif** sur toute la période projetée. 
                      Le point bas est estimé à <span className="font-bold text-slate-900 amount-blur">{formatCurrency(projection?.low_point || 0, displayCurrency)}</span>.
                    </p>
                    <div className="p-4 bg-white rounded-xl border border-blue-100 shadow-sm">
                       <p className="text-xs font-bold text-blue-800 uppercase mb-2">Conseil</p>
                       <p className="text-sm text-slate-700">Vous avez un excédent de trésorerie prévu de <span className="font-bold">{formatCurrency((projection?.projected_balance || 0) - (projection?.current_balance || 0), displayCurrency)}</span>. Envisagez un versement complémentaire vers votre compte d'épargne.</p>
                    </div>
                  </CardContent>
                </Card>
             </div>
          </div>
        </TabsContent>

        <TabsContent value="insights" className="space-y-8">
          <div className="grid gap-8 lg:grid-cols-12">
            <Card className="lg:col-span-4 shadow-sm border-slate-100 overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 text-white">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <HeartPulse className="h-5 w-5 text-emerald-400" />
                  Santé Financière
                </CardTitle>
                <CardDescription className="text-slate-400">Score global de votre situation.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col items-center justify-center py-10">
                <div className="relative flex items-center justify-center">
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
                      strokeDashoffset={552.92 - (552.92 * (insights?.health_score?.total_score || 0)) / 100}
                      strokeLinecap="round"
                      className={`${
                        (insights?.health_score?.total_score || 0) > 70 ? "text-emerald-400" : (insights?.health_score?.total_score || 0) > 40 ? "text-amber-400" : "text-rose-400"
                      } transition-all duration-1000 ease-out`}
                    />
                  </svg>
                  <div className="absolute text-center">
                    <span className="text-5xl font-black">{Math.round(insights?.health_score?.total_score || 0)}</span>
                    <span className="text-slate-400 block text-sm font-bold mt-1">/ 100</span>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 w-full mt-10">
                  {insights?.health_score?.metrics.map((m: any, i: number) => (
                    <div key={i} className="bg-slate-800/50 p-3 rounded-2xl border border-slate-700/50">
                      <p className="text-[10px] uppercase font-black text-slate-500 tracking-wider mb-1">{m.name}</p>
                      <p className="text-sm font-bold flex items-center justify-between">
                        {m.value}{m.unit}
                        <span className={`h-1.5 w-1.5 rounded-full ${m.status === 'good' ? 'bg-emerald-400' : m.status === 'warning' ? 'bg-amber-400' : 'bg-rose-400'}`} />
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="lg:col-span-8 space-y-6">
              <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-amber-500" />
                Analyse & Conseils
              </h3>
              <div className="grid gap-4">
                {insights?.insights.map((insight: any, i: number) => (
                  <Card key={i} className={`shadow-sm border-l-4 ${
                    insight.type === 'anomaly' ? 'border-l-amber-500' : 'border-l-emerald-500'
                  } hover:bg-slate-50 transition-colors`}>
                    <CardHeader className="p-5">
                      <div className="flex items-start justify-between">
                        <div className="flex gap-4">
                          <div className={`mt-1 p-2 rounded-xl ${
                            insight.type === 'anomaly' ? 'bg-amber-100 text-amber-600' : 'bg-emerald-100 text-emerald-600'
                          }`}>
                            {insight.type === 'anomaly' ? <AlertTriangle className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
                          </div>
                          <div>
                            <CardTitle className="text-lg font-bold text-slate-900">{insight.title}</CardTitle>
                            <CardDescription className="text-slate-600 mt-1">{insight.description}</CardDescription>
                          </div>
                        </div>
                        {insight.value && (
                          <Badge variant="outline" className={insight.type === 'anomaly' ? 'text-amber-700 bg-amber-50' : 'text-emerald-700 bg-emerald-50'}>
                            {insight.type === 'anomaly' ? `+${formatCurrency(insight.value)}` : insight.unit === '%' ? `${insight.value}%` : formatCurrency(insight.value)}
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                  </Card>
                ))}
                {insights?.insights.length === 0 && (
                  <div className="py-20 text-center bg-slate-50 rounded-3xl border border-dashed">
                    <p className="text-slate-400 font-medium">Tout semble sous contrôle ! Aucun insight particulier ce mois-ci.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="overview" className="space-y-8">
          <Card className="shadow-sm border-slate-100 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b pb-4">
              <CardTitle className="text-lg">Flux Financiers</CardTitle>
              <CardDescription>Visualisation des revenus vers les dépenses et l'épargne.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 h-[600px]">
              <SankeyFlow data={sankeyData} currency={displayCurrency} />
            </CardContent>
          </Card>

          <div className="grid gap-8 lg:grid-cols-12">
            <Card className="lg:col-span-8 shadow-sm border-slate-100 overflow-hidden">
              <CardHeader className="bg-slate-50/50 border-b pb-4">
                <CardTitle className="text-lg">Dépenses par catégorie</CardTitle>
                <CardDescription>Où va votre argent ce mois-ci ?</CardDescription>
              </CardHeader>
              <CardContent className="p-0 sm:p-6 h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={expensesByCategory} layout="vertical" margin={{ top: 40, right: 40, left: 40, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis type="number" hide />
                    <YAxis dataKey="category.name" type="category" width={100} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                    <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                    <Bar dataKey="total" radius={[0, 4, 4, 0]} barSize={20}>
                      {expensesByCategory.map((item, i) => (
                        <Cell key={i} fill={item.category.color || COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                    {expensesByCategory
                      .filter(item => item.category?.monthly_limit != null)
                      .map((item, i) => (
                        <ReferenceLine
                          key={`limit-${i}`}
                          x={item.category.monthly_limit}
                          yAxisId={0}
                          stroke="#f59e0b"
                          strokeDasharray="4 3"
                          strokeWidth={1.5}
                        />
                      ))}
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="lg:col-span-4 shadow-sm border-slate-100 overflow-hidden">
              <CardHeader className="bg-slate-50/50 border-b pb-4">
                <CardTitle className="text-lg">Répartition</CardTitle>
                <CardDescription>Poids des catégories.</CardDescription>
              </CardHeader>
              <CardContent className="p-6 flex flex-col items-center">
                <div className="h-[250px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                      <Pie data={expensesByCategory} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={4} dataKey="total" nameKey="category.name">
                        {expensesByCategory.map((item, i) => <Cell key={i} fill={item.category.color || COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="w-full space-y-3 mt-4">
                   {expensesByCategory.slice(0, 4).map((item, i) => (
                     <div key={i} className="flex justify-between text-sm">
                       <span className="text-slate-500 flex items-center gap-2">
                         <div className="h-4 w-4 rounded-lg flex items-center justify-center" style={{ backgroundColor: item.category.color || COLORS[i % COLORS.length] }}>
                           <IconComponent name={item.category.icon} className="h-2 w-2 text-white" />
                         </div>
                         {item.category.name}
                       </span>
                       <span className="font-bold">
                         <span className="amount-blur">{item.percentage}%</span>
                       </span>
                     </div>
                   ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {tagTotals.length > 0 && (
            <Card className="shadow-sm border-slate-100 overflow-hidden mt-8">
              <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Projets & Contextes (Tags)</CardTitle>
                  <CardDescription>Dépenses transverses sur la période.</CardDescription>
                </div>
                <Tag className="h-5 w-5 text-slate-400" />
              </CardHeader>
              <CardContent className="p-6">
                <div className="flex flex-wrap gap-4">
                  {tagTotals.map((t) => (
                    <div key={t.id} className="flex items-center gap-4 p-4 bg-white border border-slate-100 rounded-3xl shadow-sm min-w-[180px] hover:border-slate-200 transition-colors group">
                      <div className="h-10 w-10 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110" style={{ backgroundColor: t.color || "#64748b" }}>
                        <Tag className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 leading-none mb-1.5">{t.name}</p>
                        <p className="text-xl font-black text-slate-900 leading-none">{formatCurrency(t.total_eur, "EUR")}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="budgets" className="space-y-6">
          <div className="flex flex-col gap-2">
            <h2 className="text-xl font-bold text-slate-900">Suivi des budgets</h2>
            <p className="text-sm text-slate-500">Visualisez votre consommation par rapport aux limites fixées par catégorie.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {budgetAlerts.map((alert) => {
              const monthlyOver = alert.monthly_ratio != null && alert.monthly_ratio >= 1
              const annualOver = alert.annual_ratio != null && alert.annual_ratio >= 1
              const monthlyWarning = alert.monthly_ratio != null && alert.monthly_ratio >= 0.8
              const annualWarning = alert.annual_ratio != null && alert.annual_ratio >= 0.8
              
              const monthlyPct = alert.monthly_ratio != null ? Math.round(alert.monthly_ratio * 100) : null
              const annualPct = alert.annual_ratio != null ? Math.round(alert.annual_ratio * 100) : null
              
              const isOver = monthlyOver || annualOver
              const isWarning = monthlyWarning || annualWarning

              return (
                <div
                  key={alert.category_id}
                  className={`p-5 rounded-2xl border flex flex-col gap-4 transition-all shadow-sm ${
                    isOver 
                      ? "bg-rose-50 border-rose-200" 
                      : isWarning 
                        ? "bg-amber-50 border-amber-200" 
                        : "bg-white border-slate-100 hover:border-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl flex items-center justify-center shadow-sm" style={{ backgroundColor: alert.category_color || "#64748b" }}>
                      <IconComponent name={alert.category_icon} className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <p className="font-bold text-slate-900">{alert.category_name}</p>
                      <p className={`text-[10px] font-black uppercase tracking-wider ${
                        isOver ? "text-rose-500" : isWarning ? "text-amber-500" : "text-emerald-500"
                      }`}>
                        {isOver ? "Dépassement" : isWarning ? "Proche de la limite" : "Budget respecté"}
                      </p>
                    </div>
                  </div>
                  {monthlyPct != null && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs text-slate-500 font-medium">
                        <span>Mensuel — <span className="amount-blur">{formatCurrency(alert.monthly_spent)}</span> / <span className="amount-blur">{formatCurrency(alert.monthly_limit)}</span></span>
                        <span className={`font-bold amount-blur ${monthlyOver ? "text-rose-600" : monthlyWarning ? "text-amber-600" : "text-slate-600"}`}>{monthlyPct}%</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            monthlyOver ? "bg-rose-500" : monthlyWarning ? "bg-amber-400" : "bg-emerald-400"
                          }`}
                          style={{ width: `${Math.min(monthlyPct, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {annualPct != null && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs text-slate-500 font-medium">
                        <span>Annuel — <span className="amount-blur">{formatCurrency(alert.annual_spent)}</span> / <span className="amount-blur">{formatCurrency(alert.annual_limit)}</span></span>
                        <span className={`font-bold amount-blur ${annualOver ? "text-rose-600" : annualWarning ? "text-amber-600" : "text-slate-600"}`}>{annualPct}%</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            annualOver ? "bg-rose-500" : annualWarning ? "bg-amber-400" : "bg-emerald-400"
                          }`}
                          style={{ width: `${Math.min(annualPct, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
            {budgetAlerts.length === 0 && (
              <div className="col-span-full py-20 text-center bg-slate-50 rounded-3xl border border-dashed">
                <p className="text-slate-400">Aucun budget configuré. Ajoutez des limites dans les réglages des catégories.</p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="merchants" className="space-y-8">
           <Card className="shadow-sm border-slate-100 overflow-hidden">
             <CardHeader className="bg-slate-50/50 border-b pb-4">
               <div className="flex items-center gap-2">
                 <Users className="h-5 w-5 text-slate-400" />
                 <CardTitle className="text-lg">Top 10 Commerçants</CardTitle>
               </div>
               <CardDescription>Les établissements où vous dépensez le plus.</CardDescription>
             </CardHeader>
             <CardContent className="p-0 sm:p-6 h-[500px]">
               <ResponsiveContainer width="100%" height="100%">
                 <BarChart data={topMerchants} layout="vertical" margin={{ top: 40, right: 50, left: 50, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis type="number" hide />
                    <YAxis dataKey="merchant" type="category" width={150} axisLine={false} tickLine={false} tick={{ fontSize: 12, fontWeight: 500, fill: '#64748b' }} />
                    <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(v: number) => formatCurrency(v, displayCurrency)} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                    <Bar dataKey="total" fill="#0f172a" radius={[0, 4, 4, 0]} barSize={30} />
                 </BarChart>
               </ResponsiveContainer>
             </CardContent>
           </Card>
        </TabsContent>

        <TabsContent value="subscriptions" className="space-y-8">
           <div className="grid gap-8 lg:grid-cols-2">
             <Card className="shadow-sm border-slate-100 overflow-hidden">
               <CardHeader className="bg-slate-50/50 border-b pb-4">
                 <div className="flex items-center gap-2">
                   <Briefcase className="h-5 w-5 text-slate-400" />
                   <CardTitle className="text-lg">Abonnements Mensuels</CardTitle>
                 </div>
                 <CardDescription>Total ce mois: <span className="text-slate-900 font-bold amount-blur">{formatCurrency(subscriptions?.total || 0)}</span></CardDescription>
               </CardHeader>
               <CardContent className="p-6">
                 <div className="space-y-4">
                   {subscriptions?.items?.map((sub: any, i: number) => (
                     <div key={i} className="flex items-center justify-between p-4 border rounded-xl hover:bg-slate-50 transition-colors">
                       <div className="flex items-center gap-3">
                         <div className="h-10 w-10 bg-slate-900 rounded-lg flex items-center justify-center text-white text-xs font-bold uppercase">
                           {sub.merchant.substring(0, 2)}
                         </div>
                         <span className="font-medium text-slate-900">{sub.merchant}</span>
                       </div>
                       <span className="font-bold text-slate-900 amount-blur">{formatCurrency(sub.total)}</span>
                     </div>
                   ))}
                   {(subscriptions?.items?.length ?? 0) === 0 && <p className="text-center text-slate-400 py-10">Aucun abonnement détecté.</p>}
                 </div>
               </CardContent>
             </Card>

             <Card className="shadow-sm border-slate-100 overflow-hidden">
               <CardHeader className="bg-slate-50/50 border-b pb-4">
                 <CardTitle className="text-lg">Répartition Abonnements</CardTitle>
                 <CardDescription>Poids de chaque service.</CardDescription>
               </CardHeader>
               <CardContent className="p-6 h-[400px]">
                 <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                      <Pie data={subscriptions?.items || []} cx="50%" cy="50%" innerRadius={80} outerRadius={110} paddingAngle={4} dataKey="total" nameKey="merchant">
                        {subscriptions?.items?.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                    </PieChart>
                 </ResponsiveContainer>
               </CardContent>
             </Card>
           </div>
        </TabsContent>

        <TabsContent value="investments" className="space-y-8">
           <div className="grid gap-8 lg:grid-cols-2">
             <Card className="shadow-sm border-slate-100 overflow-hidden">
               <CardHeader className="bg-slate-50/50 border-b pb-4">
                 <div className="flex items-center gap-2">
                   <TrendingUp className="h-5 w-5 text-slate-400" />
                   <CardTitle className="text-lg">Versements du mois</CardTitle>
                 </div>
                 <CardDescription>Par compte d'investissement.</CardDescription>
               </CardHeader>
               <CardContent className="p-0 sm:p-6 h-[400px]">
                 <ResponsiveContainer width="100%" height="100%">
                   <BarChart 
                     data={investments?.items || []} 
                     layout="vertical" 
                     margin={{ top: 40, right: 50, left: 50, bottom: 20 }}
                     onClick={(state: any) => {
                       if (state && state.activePayload && state.activePayload.length > 0) {
                         onInvestmentBarClick(state.activePayload[0].payload);
                       }
                     }}
                     className="cursor-pointer"
                   >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis type="number" hide />
                      <YAxis dataKey="account_name" type="category" width={150} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                      <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(v: number) => formatCurrency(v, displayCurrency)} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                      <Bar dataKey="total_verse" name="Versement" fill="#0f172a" radius={[0, 4, 4, 0]} barSize={30} />
                   </BarChart>
                 </ResponsiveContainer>
               </CardContent>
             </Card>

             <Card className="shadow-sm border-slate-100 overflow-hidden">
               <CardHeader className="bg-slate-50/50 border-b pb-4">
                 <div className="flex items-center gap-2">
                   <PieChartIcon className="h-5 w-5 text-slate-400" />
                   <CardTitle className="text-lg">Répartition Patrimoine</CardTitle>
                 </div>
                 <CardDescription>Part de chaque compte investi.</CardDescription>
               </CardHeader>
               <CardContent className="p-6 h-[400px]">
                 <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                      <Pie 
                        data={allocation?.items || []} 
                        cx="50%" 
                        cy="50%" 
                        innerRadius={80} 
                        outerRadius={110} 
                        paddingAngle={4} 
                        dataKey="current_value" 
                        nameKey="account_name"
                        onClick={onAllocationClick}
                        className="cursor-pointer"
                      >
                        {allocation?.items?.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                    </PieChart>
                 </ResponsiveContainer>
               </CardContent>
             </Card>
           </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-8">
           <div className="grid gap-8 lg:grid-cols-2">
             <Card className="shadow-sm border-slate-100 overflow-hidden">
               <CardHeader className="bg-slate-50/50 border-b pb-4">
                 <div className="flex items-center gap-2">
                   <HistoryIcon className="h-5 w-5 text-slate-400" />
                   <CardTitle className="text-lg">Flux de trésorerie</CardTitle>
                 </div>
                 <CardDescription>Revenus vs Dépenses (6 mois).</CardDescription>
               </CardHeader>
               <CardContent className="p-0 sm:p-6 h-[400px]">
                 <ResponsiveContainer width="100%" height="100%">
                   <AreaChart data={kpiHistory} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
                     <defs>
                       <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient>
                       <linearGradient id="colorDep" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f43f5e" stopOpacity={0.1}/><stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/></linearGradient>
                     </defs>
                     <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                     <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                     <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
                     <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                     <Legend verticalAlign="top" height={36}/>
                     <Area type="monotone" dataKey="revenus" name="Revenus" stroke="#10b981" fill="url(#colorRev)" strokeWidth={3} />
                     <Area type="monotone" dataKey="depenses" name="Dépenses" stroke="#f43f5e" fill="url(#colorDep)" strokeWidth={3} />
                   </AreaChart>
                 </ResponsiveContainer>
               </CardContent>
             </Card>

             <Card className="shadow-sm border-slate-100 overflow-hidden">
               <CardHeader className="bg-slate-50/50 border-b pb-4">
                 <div className="flex items-center gap-2">
                   <Activity className="h-5 w-5 text-slate-400" />
                   <CardTitle className="text-lg">Évolution du Burn Rate</CardTitle>
                 </div>
                 <CardDescription>Dépense moyenne journalière par mois.</CardDescription>
               </CardHeader>
               <CardContent className="p-0 sm:p-6 h-[400px]">
                 <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={burnRateSeries} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis 
                        dataKey="month" 
                        axisLine={false} 
                        tickLine={false} 
                        tickFormatter={(v) => months[v-1]?.substring(0, 3) || v} 
                        tick={{ fontSize: 12, fill: '#64748b' }} 
                      />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
                      <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => `${v.toFixed(2)}${displayCurrency === 'EUR' ? '€' : displayCurrency} / jour`} />
                      <Line type="monotone" dataKey="burn_rate" name="Burn Rate" stroke="#0f172a" strokeWidth={4} dot={{ r: 4, fill: "#0f172a" }} />
                    </LineChart>
                 </ResponsiveContainer>
               </CardContent>
             </Card>

             <Card className="shadow-sm border-slate-100 overflow-hidden">
               <CardHeader className="bg-slate-50/50 border-b pb-4">
                 <div className="flex items-center gap-2">
                   <Layers className="h-5 w-5 text-slate-400" />
                   <CardTitle className="text-lg">Évolution du Salaire</CardTitle>
                 </div>
                 <CardDescription>Stabilité et croissance des revenus principaux.</CardDescription>
               </CardHeader>
               <CardContent className="p-0 sm:p-6 h-[400px]">
                 <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={salarySeries} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis 
                        dataKey="month" 
                        axisLine={false} 
                        tickLine={false} 
                        tickFormatter={(v) => months[v-1]?.substring(0, 3) || v} 
                        tick={{ fontSize: 12, fill: '#64748b' }} 
                      />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
                      <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                      <Line type="stepAfter" dataKey="salary" name="Salaire" stroke="#0f172a" strokeWidth={4} dot={{ r: 4, fill: "#0f172a" }} />
                    </LineChart>
                 </ResponsiveContainer>
               </CardContent>
             </Card>
           </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
