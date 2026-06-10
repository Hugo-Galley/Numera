import { useEffect, useState, useMemo } from "react"
import { Link } from "react-router-dom"
import { 
  PiggyBank, 
  TrendingUp, 
  ArrowUpRight, 
  ShieldCheck,
  Zap,
  Target,
  History,
  Info,
  Calendar,
  Layers,
  Plus,
  Pencil,
  Trash2,
  Palette,
  AlertTriangle
} from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { toast } from "sonner"

const GOAL_COLORS = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#f43f5e", "#06b6d4", "#ec4899", "#64748b"]

export default function Savings() {
  const [analytics, setAnalytics] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [goals, setGoals] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  
  const [month, setMonth] = useState<string>(String(new Date().getMonth() + 1))
  const [year, setYear] = useState<string>(String(new Date().getFullYear()))
  const [period, setPeriod] = useState<"monthly" | "all-time">("monthly")

  // Form state
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingGoal, setEditingGoal] = useState<any>(null)
  const [goalForm, setGoalForm] = useState({
    name: "",
    target_amount: "",
    keyword: "",
    color: GOAL_COLORS[0],
    deadline: "",
    account_id: "none",
    category_id: "none"
  })

  const now = new Date()

  const loadData = async () => {
    setLoading(true)
    try {
      const queryParams = period === "monthly" 
        ? `month=${month}&year=${year}`
        : ""
      
      const [budget, kpiHistory, goalsData, accs, cats] = await Promise.all([
        api.get<any>(`/analytics/budget?${queryParams}`),
        api.get<any[]>("/analytics/kpi-history?months_count=12"),
        api.get<any[]>("/goals"),
        api.get<any[]>("/accounts"),
        api.get<any[]>("/categories")
      ])
      setAnalytics(budget)
      setHistory(kpiHistory)
      setGoals(goalsData)
      setAccounts(accs)
      setCategories(cats)
    } catch (error) {
      console.error("Failed to load savings data", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [month, year, period])

  const handleCreateOrUpdateGoal = async () => {
    if (!goalForm.name || !goalForm.target_amount) {
      toast.error("Veuillez remplir les champs obligatoires (Nom et Montant)")
      return
    }

    try {
      const payload: any = {
        name: goalForm.name,
        target_amount: parseFloat(goalForm.target_amount),
        keyword: goalForm.keyword || null,
        color: goalForm.color,
        icon: "Target", 
        deadline: goalForm.deadline || null,
        account_id: goalForm.account_id === "none" ? null : parseInt(goalForm.account_id),
        category_id: goalForm.category_id === "none" ? null : parseInt(goalForm.category_id)
      }

      if (editingGoal) {
        await api.patch(`/goals/${editingGoal.id}`, payload)
        toast.success("Objectif mis à jour")
      } else {
        await api.post("/goals", payload)
        toast.success("Objectif créé")
      }
      setIsDialogOpen(false)
      setEditingGoal(null)
      setGoalForm({ name: "", target_amount: "", keyword: "", color: GOAL_COLORS[0], deadline: "", account_id: "none", category_id: "none" })
      loadData()
    } catch (error) {
      console.error("Error saving goal:", error)
      toast.error("Une erreur est survenue lors de l'enregistrement")
    }
  }

  const handleDeleteGoal = async (id: number) => {
    if (!confirm("Supprimer cet objectif ?")) return
    try {
      await api.delete(`/goals/${id}`)
      toast.success("Objectif supprimé")
      loadData()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  const openEditDialog = (goal: any) => {
    setEditingGoal(goal)
    setGoalForm({
      name: goal.name,
      target_amount: String(goal.target_amount),
      keyword: goal.keyword || "",
      color: goal.color || GOAL_COLORS[0],
      deadline: goal.deadline || "",
      account_id: goal.account_id ? String(goal.account_id) : "none",
      category_id: goal.category_id ? String(goal.category_id) : "none"
    })
    setIsDialogOpen(true)
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value)
  }

  const savingsRate = analytics?.taux_epargne || 0
  
  const getRateColor = (rate: number) => {
    if (rate >= 30) return "#10b981" // Emerald
    if (rate >= 15) return "#3b82f6" // Blue
    if (rate >= 0) return "#f59e0b" // Amber
    return "#f43f5e" // Rose
  }

  const gaugeData = useMemo(() => [
    { value: Math.max(0, Math.min(100, savingsRate)) },
    { value: 100 - Math.max(0, Math.min(100, savingsRate)) }
  ], [savingsRate])

  const months = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
  ]

  // Resilience: how many months could you live with current net worth?
  const resilienceMonths = analytics?.burn_rate > 0 
    ? (analytics.patrimoine_net_total / (analytics.burn_rate * 30.5)).toFixed(1)
    : "∞"

  return (
    <div className="space-y-10 pb-10">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">Analyse de l'Épargne</h1>
          <p className="text-slate-500 mt-1">Mesurez votre capacité d'accumulation et votre résilience financière.</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 bg-white p-1.5 rounded-xl border shadow-sm">
          <Select value={period} onValueChange={(v: any) => setPeriod(v)}>
            <SelectTrigger className="w-full sm:w-[140px] border-none shadow-none focus:ring-0 font-medium">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="monthly">Mensuel</SelectItem>
              <SelectItem value="all-time">Tout le temps</SelectItem>
            </SelectContent>
          </Select>

          {period === "monthly" && (
            <>
              <Separator orientation="vertical" className="hidden sm:block h-6" />
              <Select value={month} onValueChange={setMonth}>
                <SelectTrigger className="flex-1 sm:w-[130px] border-none shadow-none focus:ring-0">
                  <SelectValue placeholder="Mois" />
                </SelectTrigger>
                <SelectContent>
                  {months.map((m, i) => (
                    <SelectItem key={i + 1} value={String(i + 1)}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Separator orientation="vertical" className="hidden sm:block h-6" />
              <Select value={year} onValueChange={setYear}>
                <SelectTrigger className="flex-1 sm:w-[100px] border-none shadow-none focus:ring-0">
                  <SelectValue placeholder="Année" />
                </SelectTrigger>
                <SelectContent>
                  {[2024, 2025, 2026].map((y) => (
                    <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-[400px]">
           <div className="flex flex-col items-center gap-4">
             <div className="h-10 w-10 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin" />
             <p className="text-slate-500 font-medium">Analyse en cours...</p>
           </div>
        </div>
      ) : (
        <>
      <div className="grid gap-8 grid-cols-1 lg:grid-cols-4">
        {/* Modern Radial Gauge for Savings Rate */}
        <Card className="lg:col-span-1 shadow-xl border-none bg-gradient-to-br from-slate-900 to-slate-800 text-white overflow-hidden relative">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Target className="h-32 w-32" />
          </div>
          <CardHeader className="pb-0 text-center">
            <CardDescription className="text-slate-400 font-bold uppercase tracking-widest text-xs">
              Taux d'Épargne {period === "all-time" ? "Global" : "Réel"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center pt-6">
            <div className="relative h-40 w-40 sm:h-48 sm:w-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={gaugeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={window.innerWidth < 640 ? 50 : 60}
                    outerRadius={window.innerWidth < 640 ? 70 : 80}
                    startAngle={225}
                    endAngle={-45}
                    paddingAngle={0}
                    dataKey="value"
                    stroke="none"
                  >
                    <Cell fill={getRateColor(savingsRate)} />
                    <Cell fill="rgba(255,255,255,0.1)" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl sm:text-4xl font-black">{savingsRate}%</span>
                <span className="text-[10px] text-slate-400 uppercase font-bold mt-1">
                  {period === "all-time" ? "Moyenne" : "Global"}
                </span>
              </div>
            </div>
            
            <div className="w-full mt-4 space-y-3">
               <div className="flex justify-between items-center text-sm">
                 <span className="text-slate-400">Objectif</span>
                 <span className="font-bold">20.0%</span>
               </div>
               <div className="w-full bg-slate-700 h-1 rounded-full overflow-hidden">
                 <div 
                   className="h-full bg-white transition-all duration-1000" 
                   style={{ width: `${Math.min(100, (savingsRate / 20) * 100)}%` }} 
                 />
               </div>
            </div>
          </CardContent>
        </Card>

        <div className="lg:col-span-3 grid gap-6 grid-cols-1 sm:grid-cols-2 md:grid-cols-4">
          <Card className="shadow-sm border-slate-100 hover:border-emerald-200 transition-colors">
            <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
              <CardDescription className="font-medium">Épargne Liquide</CardDescription>
              <div className="h-10 w-10 bg-emerald-50 rounded-xl flex items-center justify-center">
                <PiggyBank className="h-5 w-5 text-emerald-600" />
              </div>
            </CardHeader>
            <CardContent>
              <CardTitle className="text-2xl font-bold text-emerald-600">
                <span className="amount-blur">{formatCurrency(analytics?.epargne_total || 0)}</span>
              </CardTitle>
              <p className="text-[10px] text-slate-500 mt-1">Total disponible sur livrets.</p>
              {period === "monthly" && (
                <div className="mt-2 pt-2 border-t flex justify-between text-[10px]">
                  <span className="text-slate-400">Précédent: {formatCurrency(history[history.length - 2]?.epargne || 0)}</span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-100 hover:border-blue-200 transition-colors">
            <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
              <CardDescription className="font-medium">Flux d'Épargne</CardDescription>
              <div className="h-10 w-10 bg-blue-50 rounded-xl flex items-center justify-center">
                <Zap className="h-5 w-5 text-blue-600" />
              </div>
            </CardHeader>
            <CardContent>
              <CardTitle className="text-2xl font-bold text-blue-600">
                {formatCurrency((analytics?.revenus_apres_depenses || 0) + (analytics?.investissements_du_mois || 0))}
              </CardTitle>
              <p className="text-[10px] text-slate-500 mt-1">Total épargné {period === "all-time" ? "au total" : "ce mois"}.</p>
              <div className="mt-2 pt-2 border-t text-[10px] text-slate-400 flex justify-between">
                <span>Invest: {formatCurrency(analytics?.investissements_du_mois || 0)}</span>
                <span>Cash: {formatCurrency(analytics?.revenus_apres_depenses || 0)}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-100 hover:border-amber-200 transition-colors">
            <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
              <CardDescription className="font-medium">Intérêts perçus</CardDescription>
              <div className="h-10 w-10 bg-amber-50 rounded-xl flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-amber-600" />
              </div>
            </CardHeader>
            <CardContent>
              <CardTitle className="text-2xl font-bold text-amber-600">
                {formatCurrency(analytics?.interets_totaux || 0)}
              </CardTitle>
              <p className="text-[10px] text-slate-500 mt-1">Gains passifs {period === "all-time" ? "cumulés" : "du mois"}.</p>
              <div className="mt-2 pt-2 border-t text-[10px] text-slate-400">
                <span>Ce que votre argent vous rapporte.</span>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-100 hover:border-slate-200 transition-colors">
            <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
              <CardDescription className="font-medium">Indice Résilience</CardDescription>
              <div className="h-10 w-10 bg-slate-50 rounded-xl flex items-center justify-center">
                <ShieldCheck className="h-5 w-5 text-slate-600" />
              </div>
            </CardHeader>
            <CardContent>
              <CardTitle className="text-2xl font-bold text-slate-900">{resilienceMonths} mois</CardTitle>
              <p className="text-[10px] text-slate-500 mt-1">Autonomie sans revenus.</p>
              <div className="mt-2 pt-2 border-t">
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-slate-900" 
                    style={{ width: `${Math.min(100, (Number(resilienceMonths) / 12) * 100)}%` }} 
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="sm:col-span-2 md:col-span-3 shadow-sm border-slate-100 hover:border-slate-300 transition-colors bg-slate-50/50">
            <CardContent className="p-4 sm:p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 bg-white rounded-2xl shadow-sm flex items-center justify-center shrink-0">
                  <TrendingUp className="h-6 w-6 text-slate-900" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Patrimoine Net Total</p>
                  <div className="flex items-baseline gap-2">
                    <p className="text-2xl font-black text-slate-900">{formatCurrency(analytics?.patrimoine_net_total || 0)}</p>
                    <span className="text-xs text-emerald-600 font-bold hidden sm:inline">Inclus Investissements</span>
                  </div>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild className="w-full sm:w-auto">
                <Link to="/accounts">Voir mes comptes</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-8 grid-cols-1 lg:grid-cols-2">
        <Card className="shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-slate-400" />
              <CardTitle className="text-lg">Historique d'Épargne</CardTitle>
            </div>
            <CardDescription>Répartition entre cash restant et investissements.</CardDescription>
          </CardHeader>
          <CardContent className="p-0 sm:p-6 h-[350px] sm:h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={history} margin={{ top: 40, right: 10, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}€`} domain={[0, 'auto']} />
                <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(v: number) => formatCurrency(v)} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }}/>
                <Bar dataKey="cash_flow" name="Cash Restant" stackId="a" fill="#94a3b8" radius={[0, 0, 0, 0]} barSize={window.innerWidth < 640 ? 20 : 40} />
                <Bar dataKey="investissements" name="Investissements" stackId="a" fill="#0f172a" radius={[0, 0, 0, 0]} barSize={window.innerWidth < 640 ? 20 : 40} />
                <Bar dataKey="interets" name="Intérêts" stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]} barSize={window.innerWidth < 640 ? 20 : 40} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-slate-400" />
              <CardTitle className="text-lg">Évolution du Taux (%)</CardTitle>
            </div>
            <CardDescription>Stabilité de votre effort d'épargne sur 12 mois.</CardDescription>
          </CardHeader>
          <CardContent className="p-0 sm:p-6 h-[350px] sm:h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart 
                  data={history.map(h => ({ 
                    label: h.label, 
                    rate: h.revenus > 0 ? Number((h.epargne_flow / h.revenus * 100).toFixed(1)) : 0 
                  }))} 
                  margin={{ top: 40, right: 10, left: -10, bottom: 20 }}
                >
                <defs>
                  <linearGradient id="colorRate" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f172a" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#0f172a" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}%`} domain={['auto', 'auto']} />
                <Tooltip formatter={(v: number) => [`${v}%`, "Taux"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                <Area type="monotone" dataKey="rate" stroke="#0f172a" fillOpacity={1} fill="url(#colorRate)" strokeWidth={4} dot={{ r: 4, fill: "#0f172a", strokeWidth: 2, stroke: "#fff" }} activeDot={{ r: 6 }} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Target className="h-6 w-6 text-slate-900" />
            <h2 className="text-2xl font-bold text-slate-900">Objectifs d'Épargne</h2>
          </div>
          
          <Dialog open={isDialogOpen} onOpenChange={(open) => {
            setIsDialogOpen(open)
            if (!open) {
              setEditingGoal(null)
              setGoalForm({ name: "", target_amount: "", keyword: "", color: GOAL_COLORS[0], deadline: "" })
            }
          }}>
            <DialogTrigger asChild>
              <Button className="rounded-xl shadow-sm w-full sm:w-auto">
                <Plus className="h-4 w-4 mr-2" />
                Nouvel Objectif
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px] rounded-2xl">
              <DialogHeader>
                <DialogTitle>{editingGoal ? "Modifier l'objectif" : "Créer un objectif"}</DialogTitle>
                <DialogDescription>
                  Liez votre objectif à un mot-clé, un compte ou une catégorie pour suivre l'accumulation.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="name">Nom de l'objectif</Label>
                    <Input 
                      id="name" 
                      placeholder="ex: Vacances Japon" 
                      value={goalForm.name}
                      onChange={(e) => setGoalForm({ ...goalForm, name: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="target">Montant cible (€)</Label>
                    <Input 
                      id="target" 
                      type="number" 
                      placeholder="5000" 
                      value={goalForm.target_amount}
                      onChange={(e) => setGoalForm({ ...goalForm, target_amount: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label>Lier à un compte (optionnel)</Label>
                    <Select value={goalForm.account_id} onValueChange={(v) => setGoalForm({ ...goalForm, account_id: v })}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choisir un compte" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Aucun compte</SelectItem>
                        {accounts.map(acc => (
                          <SelectItem key={acc.id} value={String(acc.id)}>{acc.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label>Lier à une catégorie (optionnel)</Label>
                    <Select value={goalForm.category_id} onValueChange={(v) => setGoalForm({ ...goalForm, category_id: v })}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choisir une catégorie" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Aucune catégorie</SelectItem>
                        {categories.map(cat => (
                          <SelectItem key={cat.id} value={String(cat.id)}>{cat.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="keyword">Mot-clé Tag (optionnel)</Label>
                    <Input 
                      id="keyword" 
                      placeholder="ex: japon" 
                      value={goalForm.keyword}
                      onChange={(e) => setGoalForm({ ...goalForm, keyword: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="deadline">Date cible (optionnel)</Label>
                    <Input 
                      id="deadline" 
                      type="date" 
                      value={goalForm.deadline}
                      onChange={(e) => setGoalForm({ ...goalForm, deadline: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label>Couleur</Label>
                  <div className="flex flex-wrap gap-2">
                    {GOAL_COLORS.map((c) => (
                      <button
                        key={c}
                        type="button"
                        className={`h-8 w-8 rounded-full border-2 transition-all ${goalForm.color === c ? 'border-slate-900 scale-110 shadow-md' : 'border-transparent'}`}
                        style={{ backgroundColor: c }}
                        onClick={() => setGoalForm({ ...goalForm, color: c })}
                      />
                    ))}
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleCreateOrUpdateGoal} className="w-full rounded-xl">
                  {editingGoal ? "Mettre à jour" : "Créer l'objectif"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal) => (
            <Card key={goal.id} className="group overflow-hidden border-slate-100 shadow-sm hover:shadow-md transition-all hover:border-slate-200">
              <CardHeader className="pb-3 flex flex-row items-start justify-between">
                <div className="flex gap-4">
                  <div 
                    className="h-12 w-12 rounded-2xl flex items-center justify-center text-white shadow-lg shrink-0"
                    style={{ backgroundColor: goal.color || "#0f172a" }}
                  >
                    <Target className="h-6 w-6" />
                  </div>
                  <div className="min-w-0">
                    <CardTitle className="text-lg font-bold truncate">{goal.name}</CardTitle>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {goal.deadline && (
                        <Badge variant="secondary" className="text-[9px] uppercase tracking-wider font-bold bg-slate-200 text-slate-700">
                          <Calendar className="h-2.5 w-2.5 mr-1" />
                          {new Date(goal.deadline).toLocaleDateString()}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full" onClick={() => openEditDialog(goal)}>
                    <Pencil className="h-4 w-4 text-slate-400" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full hover:text-rose-600" onClick={() => handleDeleteGoal(goal.id)}>
                    <Trash2 className="h-4 w-4 text-slate-400" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-2xl font-black text-slate-900">{formatCurrency(goal.current_amount)}</p>
                    <p className="text-xs text-slate-500 font-medium">sur {formatCurrency(goal.target_amount)}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex flex-col items-end">
                      <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full mb-1 ${
                        goal.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                        goal.status === 'ahead' ? 'bg-blue-100 text-blue-700' :
                        goal.status === 'behind' ? 'bg-rose-100 text-rose-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {goal.status === 'completed' ? 'Terminé' :
                         goal.status === 'ahead' ? 'En avance' :
                         goal.status === 'behind' ? 'En retard' : 'Dans les temps'}
                      </span>
                      <p className="text-xl font-black text-slate-900">{Math.round(goal.percentage)}%</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full transition-all duration-1000 rounded-full"
                      style={{ 
                        width: `${Math.min(100, goal.percentage)}%`,
                        backgroundColor: goal.color || "#0f172a"
                      }}
                    />
                  </div>
                </div>

                {goal.monthly_required && goal.percentage < 100 && (
                  <div className="flex items-center justify-between text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-100">
                    <span className="text-slate-500 font-medium italic">Besoin mensuel recommandé:</span>
                    <span className="font-bold text-slate-900">{formatCurrency(goal.monthly_required)} / mois</span>
                  </div>
                )}

                {goal.percentage >= 100 && (
                  <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 p-2 rounded-xl text-xs font-bold justify-center border border-emerald-100">
                    <Zap className="h-3 w-3 fill-emerald-600" />
                    Objectif atteint !
                  </div>
                )}

                <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-50">
                   {goal.account_id && (
                     <Badge variant="outline" className="text-[9px] py-0 h-5 bg-white border-slate-200">
                       <Layers className="h-2.5 w-2.5 mr-1 text-slate-400" />
                       {accounts.find(a => a.id === goal.account_id)?.name || "Compte"}
                     </Badge>
                   )}
                   {goal.category_id && (
                     <Badge variant="outline" className="text-[9px] py-0 h-5 bg-white border-slate-200">
                       <Tag className="h-2.5 w-2.5 mr-1 text-slate-400" />
                       {categories.find(c => c.id === goal.category_id)?.name || "Catégorie"}
                     </Badge>
                   )}
                   {goal.keyword && (
                     <Badge variant="outline" className="text-[9px] py-0 h-5 bg-white border-slate-200">
                       <Info className="h-2.5 w-2.5 mr-1 text-slate-400" />
                       TAG: {goal.keyword}
                     </Badge>
                   )}
                </div>
              </CardContent>
            </Card>
          ))}
          {goals.length === 0 && (
            <div className="col-span-full py-16 text-center border-2 border-dashed border-slate-200 rounded-[2rem] bg-slate-50/50">
              <div className="mx-auto h-16 w-16 bg-white rounded-3xl shadow-sm flex items-center justify-center mb-4">
                <Target className="h-8 w-8 text-slate-300" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Aucun objectif actif</h3>
              <p className="text-slate-500 text-sm max-w-xs mx-auto mt-2">
                Commencez par créer un objectif pour suivre vos projets financiers.
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-slate-900 text-white p-6 sm:p-10 rounded-[2rem] shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -mr-32 -mt-32 blur-3xl" />
        <div className="relative flex flex-col md:flex-row items-center gap-6 sm:gap-10">
          <div className="h-20 w-20 sm:h-24 sm:w-24 bg-white/10 rounded-3xl backdrop-blur-md flex items-center justify-center flex-shrink-0 border border-white/20">
            <PiggyBank className="h-10 w-10 sm:h-12 sm:w-12 text-white" />
          </div>
          <div className="space-y-4 text-center md:text-left">
            <h3 className="text-2xl sm:text-3xl font-black tracking-tight">Conseil Stratégique</h3>
            <p className="text-slate-400 max-w-2xl leading-relaxed text-sm sm:text-lg">
              Votre autonomie financière est de <span className="font-bold text-white">{resilienceMonths} mois</span>. 
              {Number(resilienceMonths) >= 12 
                ? " Vous avez une résilience exceptionnelle. C'est le moment idéal pour optimiser votre allocation vers des actifs à plus haut rendement." 
                : Number(resilienceMonths) >= 6
                ? " Votre situation est solide. Vous pouvez commencer à automatiser vos investissements long-terme."
                : " Concentrez-vous sur la construction de votre épargne de précaution pour atteindre le palier des 6 mois."}
            </p>
            <div className="pt-2 sm:pt-4 flex flex-wrap justify-center md:justify-start gap-2 sm:gap-4">
               <Badge className="bg-white/10 text-white border-white/20 px-3 sm:px-4 py-1">Stratégie: {Number(resilienceMonths) >= 6 ? "Accumulation" : "Sécurisation"}</Badge>
               <Badge className="bg-white/10 text-white border-white/20 px-3 sm:px-4 py-1">Risque: Modéré</Badge>
            </div>
          </div>
        </div>
      </div>
      </>
      )}
    </div>
  )
}
