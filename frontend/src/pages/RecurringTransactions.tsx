import { useEffect, useState } from "react"
import {
  Plus,
  Repeat,
  Trash2,
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Pencil,
  CreditCard,
  TrendingUp,
  Clock,
  RefreshCw,
  Search,
  Filter,
  CalendarIcon,
  ChevronDown,
  Sparkles
} from "lucide-react"

const MONTHS = [
  { value: 1, label: "Jan" },
  { value: 2, label: "Fév" },
  { value: 3, label: "Mar" },
  { value: 4, label: "Avr" },
  { value: 5, label: "Mai" },
  { value: 6, label: "Juin" },
  { value: 7, label: "Juil" },
  { value: 8, label: "Août" },
  { value: 9, label: "Sep" },
  { value: 10, label: "Oct" },
  { value: 11, label: "Nov" },
  { value: 12, label: "Déc" },
]
import { api } from "@/lib/api"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { SecuritySearchInput } from "@/components/investments/SecuritySearchInput"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { toast } from "sonner"
import { format } from "date-fns"
import { fr } from "date-fns/locale"
import { cn } from "@/lib/utils"
import { COUNTRIES } from "@/lib/countries"
import { SalaryManager } from "@/components/tools/SalaryManager"

type Category = {
  id: number
  name: string
  color: string
}

type Account = {
  id: number
  name: string
  currency: string
  type: "courant" | "epargne" | "investissement"
}

type RecurringTransaction = {
  id: number
  account_id: number
  name: string
  type: string
  amount: number
  currency: string
  category_id: number | null
  frequency: string
  day_of_month: number | null
  excluded_months?: number[] | null
  start_date: string
  end_date: string | null
  last_generated_date: string | null
  is_active: boolean
  auto_generate: boolean
  note: string | null
  transfer_to_account_id?: number | null
  asset_class?: string | null
  sector?: string | null
  geographic_zone?: string | null
  ticker?: string | null
  isin?: string | null
  quantity?: number | null
  unit_price?: number | null
  etf_profile_id?: number | null
  category?: Category
}

export default function RecurringTransactions() {
  const [recurringTxs, setRecurringTxs] = useState<RecurringTransaction[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [subsData, setSubsData] = useState<any>(null)
  const [suggestions, setSuggestions] = useState<{
    asset_classes: string[],
    sectors: string[],
    geographic_zones: string[]
  }>({ asset_classes: [], sectors: [], geographic_zones: [] })
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState("recurring")
  const [subTab, setSubTab] = useState<"subscriptions" | "investments">("subscriptions")
  
  // Dialogs
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingTx, setEditingTx] = useState<RecurringTransaction | null>(null)
  const [isIrregularSubmenuOpen, setIsIrregularSubmenuOpen] = useState(false)
  const [isManualQuantityOpen, setIsManualQuantityOpen] = useState(false)

  // Form State
  const [formData, setFormData] = useState({
    account_id: "",
    name: "",
    type: "Sortie",
    amount: "",
    currency: "EUR",
    category_id: "none",
    frequency: "monthly",
    day_of_month: "1",
    excluded_months: [] as number[],
    start_date: format(new Date(), "yyyy-MM-dd"),
    is_active: true,
    auto_generate: false,
    transfer_to_account_id: "none",
    note: "",
    asset_class: "",
    sector: "",
    geographic_zone: "",
    ticker: "",
    isin: "",
    quantity: "",
    unit_price: "",
    etf_profile_id: null as number | null,
  })

  const selectedAccount = accounts.find(a => a.id.toString() === formData.account_id)
  // Virement vers un compte investissement : la sortie et le dépôt + achat de parts sont créés ensemble
  const transferDest = accounts.find(a => a.id.toString() === formData.transfer_to_account_id)
  const transferToInvestment = formData.type === "Sortie" && selectedAccount?.type !== "investissement" && transferDest?.type === "investissement"
  const isInvestment = selectedAccount?.type === "investissement" || (!!formData.ticker && !transferToInvestment)
  const showSecurities = isInvestment || transferToInvestment

  const allSubs = subsData?.subscriptions || []
  const activeSubs = allSubs.filter((s: any) => {
    if (!s.is_recurring_entity) return false
    const isInv = s.category_name === "Investissement" || s.category_name === "Epargne"
    return subTab === "investments" ? isInv : !isInv
  })
  
  const potentialSubs = allSubs.filter((s: any) => {
    if (s.is_recurring_entity) return false
    const isInv = s.category_name === "Investissement" || s.category_name === "Epargne"
    return subTab === "investments" ? isInv : !isInv
  })

  const loadData = async () => {
    setLoading(true)
    try {
      const [txsData, accountsData, categoriesData, sData, suggestionsData] = await Promise.all([
        api.get<RecurringTransaction[]>("/recurring-transactions/"),
        api.get<Account[]>("/accounts"),
        api.get<Category[]>("/categories"),
        api.get<any>("/analytics/subscriptions"),
        api.get<any>("/analytics/asset-allocation/suggestions")
      ])
      setRecurringTxs(txsData || [])
      setAccounts(accountsData?.filter(a => a) || [])
      setCategories(categoriesData || [])
      setSubsData(sData)
      if (suggestionsData) setSuggestions(suggestionsData)
    } catch (error) {
      console.error("Error loading data:", error)
      toast.error("Erreur lors du chargement des données")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleOpenCreate = () => {
    setEditingTx(null)
    setIsIrregularSubmenuOpen(false)
    setIsManualQuantityOpen(false)
    const firstAccount = accounts[0]
    setFormData({
      account_id: firstAccount?.id.toString() || "",
      name: "",
      type: firstAccount?.type === "investissement" ? "versement" : "Sortie",
      amount: "",
      currency: firstAccount?.currency || "EUR",
      category_id: "none",
      frequency: "monthly",
      day_of_month: "1",
      excluded_months: [],
      start_date: format(new Date(), "yyyy-MM-dd"),
      is_active: true,
      auto_generate: false,
      transfer_to_account_id: "none",
      note: "",
      asset_class: "",
      sector: "",
      geographic_zone: "",
      ticker: "",
      isin: "",
      quantity: "",
      unit_price: "",
      etf_profile_id: null,
    })
    setIsFormOpen(true)
  }

  const handleOpenEdit = (tx: RecurringTransaction) => {
    setEditingTx(tx)
    setIsIrregularSubmenuOpen(Boolean(tx.excluded_months && tx.excluded_months.length > 0))
    setIsManualQuantityOpen(Boolean(tx.quantity && tx.quantity > 0))
    setFormData({
      account_id: tx.account_id.toString(),
      name: tx.name,
      type: tx.type,
      amount: tx.amount.toString(),
      currency: tx.currency,
      category_id: tx.category_id?.toString() || "none",
      frequency: tx.frequency,
      day_of_month: tx.day_of_month?.toString() || "1",
      excluded_months: tx.excluded_months || [],
      start_date: format(new Date(tx.start_date), "yyyy-MM-dd"),
      is_active: tx.is_active,
      auto_generate: tx.auto_generate,
      transfer_to_account_id: tx.transfer_to_account_id?.toString() || "none",
      note: tx.note || "",
      asset_class: tx.asset_class || "",
      sector: tx.sector || "",
      geographic_zone: tx.geographic_zone || "",
      ticker: tx.ticker || "",
      isin: tx.isin || "",
      quantity: tx.quantity != null ? tx.quantity.toString() : "",
      unit_price: tx.unit_price != null ? tx.unit_price.toString() : "",
      etf_profile_id: tx.etf_profile_id || null,
    })
    setIsFormOpen(true)
  }

  const handleSubmit = async () => {
    if (!formData.name || !formData.amount || !formData.account_id) {
      toast.error("Veuillez remplir les champs obligatoires")
      return
    }

    const payload = {
      ...formData,
      account_id: parseInt(formData.account_id),
      amount: parseFloat(formData.amount),
      category_id: formData.category_id === "none" ? null : parseInt(formData.category_id),
      transfer_to_account_id: formData.type === "Sortie" && formData.transfer_to_account_id !== "none" ? parseInt(formData.transfer_to_account_id) : null,
      day_of_month: parseInt(formData.day_of_month),
      excluded_months: formData.frequency === "monthly" && formData.excluded_months.length > 0 ? formData.excluded_months : null,
      start_date: new Date(formData.start_date).toISOString(),
      asset_class: formData.asset_class || null,
      sector: formData.sector || null,
      geographic_zone: formData.geographic_zone || null,
      ticker: showSecurities && formData.ticker ? formData.ticker.trim().toUpperCase() : null,
      isin: formData.isin ? formData.isin.trim().toUpperCase() : null,
      quantity: formData.quantity ? parseFloat(formData.quantity) : null,
      unit_price: formData.unit_price ? parseFloat(formData.unit_price) : null,
      etf_profile_id: formData.etf_profile_id || null,
    }

    try {
      if (editingTx) {
        await api.patch(`/recurring-transactions/${editingTx.id}`, payload)
        toast.success("Transaction récurrente mise à jour")
      } else {
        await api.post("/recurring-transactions/", payload)
        toast.success("Transaction récurrente créée")
      }
      setIsFormOpen(false)
      loadData()
    } catch (error) {
      console.error("Error saving recurring tx:", error)
      toast.error("Erreur lors de l'enregistrement")
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("Êtes-vous sûr de vouloir supprimer cette récurrence ?")) return
    try {
      await api.delete(`/recurring-transactions/${id}`)
      toast.success("Transaction récurrente supprimée")
      loadData()
    } catch (error) {
      console.error("Error deleting recurring tx:", error)
      toast.error("Erreur lors de la suppression")
    }
  }

  const handleTrigger = async () => {
    try {
      const count = await api.post<number>("/recurring-transactions/trigger", {})
      toast.success(`${count} transaction(s) générée(s)`)
      loadData()
    } catch (error) {
      console.error("Error triggering generation:", error)
      toast.error("Erreur lors de la génération")
    }
  }

  const toggleActive = async (tx: RecurringTransaction) => {
    try {
      await api.patch(`/recurring-transactions/${tx.id}`, { is_active: !tx.is_active })
      loadData()
    } catch (error) {
      toast.error("Erreur lors de la modification")
    }
  }

  const handleOpenValidate = (potential: any, isInvest: boolean = false) => {
    setEditingTx(null)
    setIsIrregularSubmenuOpen(false)
    
    let acc = accounts[0]
    if (isInvest) {
      const invAcc = accounts.find(a => a.type === "investissement")
      if (invAcc) acc = invAcc
    }

    setFormData({
      account_id: acc?.id.toString() || "",
      name: potential.name,
      type: isInvest ? "versement" : "Sortie",
      amount: potential.amount.toString(),
      currency: acc?.currency || "EUR",
      category_id: categories.find(c => c.name === potential.category_name)?.id.toString() || "none",
      frequency: "monthly",
      day_of_month: "1",
      excluded_months: [],
      start_date: format(new Date(), "yyyy-MM-dd"),
      is_active: true,
      auto_generate: false,
      transfer_to_account_id: "none",
      note: isInvest ? "Validé comme investissement" : "Validé depuis détection automatique",
      asset_class: "",
      sector: "",
      geographic_zone: "",
      ticker: "",
      isin: "",
      quantity: "",
      unit_price: "",
      etf_profile_id: null,
    })
    setIsFormOpen(true)
  }

  const handleIgnoreDetection = async (potential: any) => {
    if (!confirm(`Ne plus suggérer "${potential.name}" (${formatCurrency(potential.amount)}) comme abonnement ?`)) return
    try {
      await api.post("/analytics/subscriptions/ignore", {
        merchant: potential.name,
        amount: potential.amount
      })
      toast.success("Suggestion ignorée")
      loadData()
    } catch (error) {
      console.error("Error ignoring detection:", error)
      toast.error("Erreur lors de l'opération")
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value || 0)
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Récurrences & Abonnements</h1>
          <p className="text-slate-500">Anticipez vos charges fixes et gérez vos flux automatiques.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleTrigger} className="gap-2">
            <Play className="h-4 w-4" />
            Lancer la génération
          </Button>
          <Button onClick={handleOpenCreate} className="gap-2">
            <Plus className="h-4 w-4" />
            Nouvelle récurrence
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="bg-slate-100 p-1">
          <TabsTrigger value="recurring" className="rounded-lg gap-2">
            <Repeat className="h-4 w-4" />
            Liste des Récurrences
          </TabsTrigger>
          <TabsTrigger value="subscriptions" className="rounded-lg gap-2">
            <CreditCard className="h-4 w-4" />
            Analyse Abonnements
          </TabsTrigger>
          <TabsTrigger value="salary" className="rounded-lg gap-2">
            <CreditCard className="h-4 w-4" />
            Salaire & Avantages
          </TabsTrigger>
        </TabsList>

        <TabsContent value="recurring" className="space-y-6">
          <Card className="shadow-sm border-slate-100">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">Toutes les récurrences</CardTitle>
              <CardDescription>
                {recurringTxs.length} récurrence(s) configurée(s) au total.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader className="bg-slate-50/50">
                  <TableRow>
                    <TableHead>Nom</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Montant</TableHead>
                    <TableHead>Fréquence</TableHead>
                    <TableHead>Dernière Gen.</TableHead>
                    <TableHead className="text-center">Auto</TableHead>
                    <TableHead className="text-center">Actif</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-12 text-slate-400 italic">
                        Chargement des récurrences...
                      </TableCell>
                    </TableRow>
                  ) : recurringTxs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-12 text-slate-400 italic">
                        Aucune transaction récurrente configurée.
                      </TableCell>
                    </TableRow>
                  ) : (
                    recurringTxs.map((tx) => (
                      <TableRow key={tx.id} className="group hover:bg-slate-50 transition-colors">
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <CompanyLogo
                              ticker={tx.ticker || undefined}
                              name={tx.name}
                              isin={tx.isin || undefined}
                              className="h-8 w-8 rounded-lg shadow-2xs shrink-0"
                            />
                            <div className="flex flex-col min-w-0">
                              <span className="font-bold text-slate-900 text-sm truncate max-w-[260px]" title={tx.name}>
                                {tx.name}
                              </span>
                              <div className="text-[11px] text-slate-500 font-medium mt-0.5 flex items-center gap-1.5 flex-wrap">
                                {tx.ticker && (
                                  <>
                                    <span className="font-mono text-slate-400 text-[10px] font-semibold uppercase">{tx.ticker}</span>
                                    <span className="text-slate-300">•</span>
                                  </>
                                )}
                                <span className="text-slate-600">{accounts.find(a => a.id === tx.account_id)?.name}</span>
                                {tx.transfer_to_account_id && (
                                  <span className="font-medium text-indigo-600">→ {accounts.find(a => a.id === tx.transfer_to_account_id)?.name}</span>
                                )}
                                <span>•</span>
                                {tx.quantity != null && tx.quantity > 0 ? (
                                  <>
                                    <span>•</span>
                                    <span className="font-semibold text-slate-700 font-mono">
                                      {tx.quantity} part{tx.quantity > 1 ? "s" : ""}
                                      {tx.unit_price ? ` @ ${tx.unit_price}€` : ""}
                                    </span>
                                  </>
                                ) : tx.ticker ? (
                                  <>
                                    <span>•</span>
                                    <span className="text-[9px] text-blue-700 font-semibold bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200/60 inline-flex items-center gap-1">
                                      <Sparkles className="h-2.5 w-2.5 text-blue-500" />
                                      Parts auto
                                      {tx.unit_price ? ` (~${(tx.amount / tx.unit_price).toFixed(2)}p)` : ""}
                                    </span>
                                  </>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={(tx.type === "Entree" || tx.type === "Interets" || tx.type === "versement" || tx.type === "dividende") ? "default" : "secondary"} className="text-[10px] h-5">
                            {tx.type}
                          </Badge>
                        </TableCell>
                        <TableCell className={`font-black ${(tx.type === "Entree" || tx.type === "Interets" || tx.type === "versement" || tx.type === "dividende") ? "text-emerald-600" : "text-slate-900"}`}>
                          {(tx.type === "Sortie" || tx.type === "retrait") ? "-" : "+"}
                          {tx.amount.toLocaleString("fr-FR", { style: "currency", currency: tx.currency })}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm font-medium capitalize text-slate-700">{tx.frequency}</div>
                          <div className="text-[10px] text-slate-400 font-bold">JOUR {tx.day_of_month}</div>
                          {tx.excluded_months && tx.excluded_months.length > 0 && (
                            <div className="mt-1">
                              <Badge variant="outline" className="text-[9px] h-4 px-1.5 text-amber-700 border-amber-200 bg-amber-50 font-medium whitespace-nowrap">
                                {tx.excluded_months.length} mois exclu{tx.excluded_months.length > 1 ? "s" : ""}
                              </Badge>
                            </div>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-slate-600">
                            {tx.last_generated_date 
                              ? format(new Date(tx.last_generated_date), "dd MMM yyyy", { locale: fr })
                              : "Aucune"
                            }
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          {tx.auto_generate ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                          ) : (
                            <XCircle className="h-4 w-4 text-slate-200 mx-auto" />
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <Checkbox 
                            checked={tx.is_active} 
                            onCheckedChange={() => toggleActive(tx)} 
                            className="rounded-md"
                          />
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-900" onClick={() => handleOpenEdit(tx)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-red-600" onClick={() => handleDelete(tx.id)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="subscriptions" className="space-y-8">
           <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
             <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl w-fit">
               <Button 
                variant={subTab === "subscriptions" ? "white" : "ghost"} 
                size="sm" 
                className={`rounded-lg font-bold text-xs px-4 ${subTab === "subscriptions" ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
                onClick={() => setSubTab("subscriptions")}
               >
                 Abonnements
               </Button>
               <Button 
                variant={subTab === "investments" ? "white" : "ghost"} 
                size="sm" 
                className={`rounded-lg font-bold text-xs px-4 ${subTab === "investments" ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
                onClick={() => setSubTab("investments")}
               >
                 Investissements
               </Button>
             </div>
             
             <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">
               {activeSubs.length} Confirmés • {potentialSubs.length} Potentiels
             </div>
           </div>

           <div className="grid gap-6 md:grid-cols-3">
             <Card className="shadow-sm border-slate-100">
               <CardHeader className="pb-2">
                 <CardDescription className="font-medium text-slate-500">
                    {subTab === "subscriptions" ? "Coût Mensuel Total" : "Versement Mensuel"}
                 </CardDescription>
               </CardHeader>
               <CardContent>
                 <CardTitle className="text-3xl font-bold text-slate-900">
                   {formatCurrency(activeSubs.reduce((acc: number, s: any) => acc + s.monthly_cost, 0))}
                 </CardTitle>
                 <p className="text-xs text-slate-400 mt-1">
                   {subTab === "subscriptions" ? "Prélevé automatiquement chaque mois" : "Moyenne mensuelle investie"}
                 </p>
               </CardContent>
             </Card>

             <Card className="shadow-sm border-slate-100">
               <CardHeader className="pb-2">
                 <CardDescription className="font-medium text-slate-500">
                   {subTab === "subscriptions" ? "Impact Annuel" : "Total Annuel Projeté"}
                 </CardDescription>
               </CardHeader>
               <CardContent>
                 <CardTitle className="text-3xl font-bold text-slate-900">
                   {formatCurrency(activeSubs.reduce((acc: number, s: any) => acc + s.annual_cost, 0))}
                 </CardTitle>
                 <p className="text-xs text-slate-400 mt-1">
                   {subTab === "subscriptions" ? "Budget total sur 12 mois" : "Objectif d'investissement annuel"}
                 </p>
               </CardContent>
             </Card>

             <Card className="shadow-sm border-slate-100">
               <CardHeader className="pb-2">
                 <CardDescription className="font-medium text-slate-500">
                   {subTab === "subscriptions" ? "Services actifs" : "Plans d'investissement"}
                 </CardDescription>
               </CardHeader>
               <CardContent>
                 <CardTitle className="text-3xl font-bold text-slate-900">
                   {activeSubs.length}
                 </CardTitle>
                 <p className="text-xs text-slate-400 mt-1">{potentialSubs.length} détections en attente</p>
               </CardContent>
             </Card>
           </div>

           <div className="grid gap-8 lg:grid-cols-12">
             <div className="lg:col-span-8 space-y-6">
                <Card className="shadow-sm border-slate-100 overflow-hidden">
                  <CardHeader className="border-b bg-slate-50/30">
                    <CardTitle className="text-lg">
                      {subTab === "subscriptions" ? "Abonnements confirmés" : "Investissements programmés"}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="divide-y">
                      {activeSubs.length === 0 ? (
                        <div className="p-12 text-center">
                          <Clock className="h-8 w-8 text-slate-200 mx-auto mb-3" />
                          <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Aucun élément</p>
                        </div>
                      ) : (
                        activeSubs.map((sub: any, i: number) => (
                          <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors group">
                            <div className="flex items-center gap-4">
                              <CompanyLogo
                                ticker={sub.ticker}
                                name={sub.name}
                                className="h-12 w-12 rounded-2xl shrink-0 shadow-sm"
                              />
                              <div>
                                <div className="flex items-center gap-2">
                                  <p className="font-bold text-slate-900">{sub.name}</p>
                                  <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-none text-[9px] h-4 px-1.5 font-black uppercase">Certifié</Badge>
                                </div>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{sub.category_name}</span>
                                  <span className="text-slate-300">•</span>
                                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{sub.frequency}</span>
                                </div>
                              </div>
                            </div>
                            <div className="text-right flex items-center gap-6">
                              <div className="hidden sm:block text-right">
                                <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest">Prochain</p>
                                <p className="text-sm font-bold text-slate-700">
                                  {safeFormat(sub.next_occurrence, "d MMM")}
                                </p>
                              </div>
                              <div>
                                <p className="text-lg font-black text-slate-900">{formatCurrency(sub.amount)}</p>
                                <p className="text-[10px] font-bold text-slate-400 text-right">
                                  {subTab === "subscriptions" ? `${formatCurrency(sub.monthly_cost)}/mois` : "Versé"}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>

                {potentialSubs.length > 0 && (
                  <Card className={`shadow-sm border-amber-100 ${subTab === 'subscriptions' ? 'bg-amber-50/10' : 'bg-indigo-50/10 border-indigo-100'}`}>
                    <CardHeader className={`flex flex-row items-center justify-between border-b ${subTab === 'subscriptions' ? 'border-amber-100/50' : 'border-indigo-100/50'}`}>
                      <div>
                        <CardTitle className={`text-lg flex items-center gap-2 ${subTab === 'subscriptions' ? 'text-amber-900' : 'text-indigo-900'}`}>
                          {subTab === 'subscriptions' ? <AlertCircle className="h-5 w-5 text-amber-500" /> : <TrendingUp className="h-5 w-5 text-indigo-500" />}
                          Détections intelligentes
                        </CardTitle>
                        <CardDescription className={subTab === 'subscriptions' ? 'text-amber-700/70' : 'text-indigo-700/70'}>
                          {subTab === 'subscriptions' ? "Abonnements potentiels trouvés dans votre historique." : "Investissements réguliers détectés."}
                        </CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className={`divide-y border-t ${subTab === 'subscriptions' ? 'border-amber-100' : 'border-indigo-100'}`}>
                        {potentialSubs.map((sub: any, i: number) => (
                          <div key={i} className="p-4 flex items-center justify-between group">
                            <div className="flex items-center gap-4">
                              <CompanyLogo
                                ticker={sub.ticker}
                                name={sub.name}
                                className="h-12 w-12 rounded-2xl shrink-0 shadow-sm"
                              />
                              <div>
                                <p className="font-bold text-slate-900">{sub.name}</p>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className={`text-[10px] font-black uppercase tracking-widest ${subTab === 'subscriptions' ? 'text-amber-600' : 'text-indigo-600'}`}>Récurrence détectée</span>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="text-right">
                                <p className="text-lg font-black text-slate-900">{formatCurrency(sub.amount)}</p>
                                <p className="text-[10px] font-bold text-slate-400 uppercase">Valider ?</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button size="sm" variant="ghost" className="text-slate-400 hover:text-red-600 h-8 px-2" onClick={() => handleIgnoreDetection(sub)}>
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                                {subTab === "subscriptions" && (
                                  <Button size="sm" variant="outline" className="border-slate-200 text-slate-600 hover:bg-slate-100 rounded-xl font-bold h-8 text-[11px]" onClick={() => handleOpenValidate(sub, true)}>
                                    Invest.
                                  </Button>
                                )}
                                <Button size="sm" variant="outline" className={`rounded-xl font-bold h-8 text-[11px] ${subTab === 'subscriptions' ? 'border-amber-200 text-amber-700 hover:bg-amber-100' : 'border-indigo-200 text-indigo-700 hover:bg-indigo-100'}`} onClick={() => handleOpenValidate(sub, subTab === "investments")}>
                                  Confirmer
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
             </div>

             <div className="lg:col-span-4 space-y-6">
                <Card className="shadow-sm border-slate-100">
                  <CardHeader className="bg-slate-50/50 border-b pb-4">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <TrendingUp className={`h-5 w-5 ${subTab === 'subscriptions' ? 'text-emerald-500' : 'text-indigo-500'}`} />
                      {subTab === "subscriptions" ? "Optimisation" : "Allocation"}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
                    <div>
                      <p className="text-sm font-medium text-slate-900 mb-2">Poids sur votre budget</p>
                      <div className="space-y-1.5">
                         <div className="flex justify-between text-xs font-bold">
                           <span className="text-slate-500">Flux mensuel</span>
                           <span className="text-slate-900">{formatCurrency(activeSubs.reduce((acc: number, s: any) => acc + s.monthly_cost, 0))}</span>
                         </div>
                         <Progress value={subTab === "subscriptions" ? 8.4 : 15.2} className="h-2 bg-slate-100" indicatorClassName={subTab === "subscriptions" ? "bg-blue-500" : "bg-indigo-500"} />
                      </div>
                    </div>
                    <div className={`p-4 rounded-xl border ${subTab === 'subscriptions' ? 'bg-emerald-50 border-emerald-100' : 'bg-indigo-50 border-indigo-100'}`}>
                      <p className={`text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 mb-1 ${subTab === 'subscriptions' ? 'text-emerald-800' : 'text-indigo-800'}`}>
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Conseil
                      </p>
                      <p className={`text-sm font-medium leading-relaxed ${subTab === 'subscriptions' ? 'text-emerald-900' : 'text-indigo-900'}`}>
                        {subTab === "subscriptions" ? (
                          <>Passez vos abonnements mensuels en <span className="font-black underline decoration-emerald-200 underline-offset-2">annuel</span> pour économiser en moyenne <span className="font-black text-emerald-700">15%</span> par an.</>
                        ) : (
                          <>L'investissement <span className="font-black underline decoration-indigo-200 underline-offset-2">automatique</span> (DCA) est la meilleure stratégie pour lisser la volatilité des marchés.</>
                        )}
                      </p>
                    </div>
                  </CardContent>
                </Card>
             </div>
           </div>
        </TabsContent>
        
        <TabsContent value="salary" className="space-y-6">
          <SalaryManager />
        </TabsContent>
      </Tabs>

      {/* Form Dialog */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingTx ? "Modifier" : "Nouvelle"} récurrence</DialogTitle>
            <DialogDescription>
              Configurez une transaction qui se répète automatiquement.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nom / Marchand</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Loyer, Netflix, Salaire..."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="type">Type</Label>
                <Select
                  value={formData.type}
                  onValueChange={(v) => setFormData({ ...formData, type: v })}
                >
                  <SelectTrigger id="type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {!isInvestment ? (
                      <>
                        <SelectItem value="Sortie">Sortie</SelectItem>
                        <SelectItem value="Entree">Entrée</SelectItem>
                        <SelectItem value="Interets">Intérêts</SelectItem>
                      </>
                    ) : (
                      <>
                        <SelectItem value="versement">Versement</SelectItem>
                        <SelectItem value="retrait">Retrait</SelectItem>
                        <SelectItem value="dividende">Dividende</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="amount">Montant</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                />
              </div>
            </div>

            {/* Investment Asset DCA block */}
            <div className="grid gap-3 p-3.5 border rounded-lg bg-slate-50/70">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CompanyLogo
                    ticker={formData.ticker}
                    name={formData.name}
                    isin={formData.isin}
                    className="h-5 w-5 rounded-xs shrink-0"
                  />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Actif Boursier / Titre (ETF, Action)
                  </span>
                </div>
                <Badge variant="outline" className="text-[10px] font-normal">
                  Optionnel
                </Badge>
              </div>

              <SecuritySearchInput
                ticker={formData.ticker}
                isin={formData.isin}
                name={formData.name}
                unitPrice={formData.unit_price}
                onSelectAsset={(asset) => {
                  setFormData((prev) => {
                    const p = asset.price_eur || asset.price || prev.unit_price
                    return {
                      ...prev,
                      name: prev.name.trim() ? prev.name : asset.name,
                      ticker: asset.symbol,
                      isin: asset.isin || prev.isin,
                      unit_price: p ? p.toString() : prev.unit_price,
                      asset_class: asset.type === "ETF" ? "ETF" : "Actions",
                      etf_profile_id: asset.etf_profile_id || null,
                    }
                  })
                }}
                onChangeTicker={(t) => setFormData((prev) => ({ ...prev, ticker: t }))}
                onChangeIsin={(isin) => setFormData((prev) => ({ ...prev, isin }))}
                onChangeName={(name) => setFormData((prev) => ({ ...prev, name }))}
              />

              {/* Automatic Shares Calculation (DCA) or Manual Override */}
              {formData.ticker && (
                <div className="space-y-2 pt-1 border-t border-slate-200/60">
                  <div className="p-3 bg-blue-50/70 border border-blue-200/60 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-blue-900">
                        <Sparkles className="h-3.5 w-3.5 text-blue-600" />
                        <span>Calcul automatique des parts (DCA)</span>
                      </div>
                      <Badge variant="outline" className="text-[10px] bg-white text-blue-700 border-blue-200 font-semibold">
                        Auto
                      </Badge>
                    </div>
                    <p className="text-[11px] text-blue-800/80 leading-relaxed">
                      Le nombre de parts sera calculé automatiquement le jour de chaque transaction au cours réel du marché (<code className="font-mono text-[10px] bg-blue-100/60 px-1 py-0.5 rounded">Parts = Montant / Cours</code>).
                    </p>
                    {formData.amount && formData.unit_price && Number(formData.unit_price) > 0 && (
                      <div className="pt-1.5 text-[11px] font-semibold text-blue-900 flex items-center justify-between border-t border-blue-200/40">
                        <span className="text-blue-700/80">Estimation au cours actuel ({Number(formData.unit_price).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €) :</span>
                        <span className="font-mono font-bold text-blue-950 bg-white px-2 py-0.5 rounded shadow-xs">
                          ~ {(Number(formData.amount) / Number(formData.unit_price)).toFixed(4)} parts
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-0.5">
                    <button
                      type="button"
                      onClick={() => setIsManualQuantityOpen(!isManualQuantityOpen)}
                      className="text-[11px] text-slate-500 hover:text-slate-800 font-medium underline underline-offset-2"
                    >
                      {isManualQuantityOpen ? "Masquer la saisie manuelle de parts" : "Fixer un nombre de parts précis (Optionnel)"}
                    </button>
                    {isManualQuantityOpen && formData.quantity && (
                      <button
                        type="button"
                        onClick={() => {
                          setFormData(prev => ({ ...prev, quantity: "" }))
                          setIsManualQuantityOpen(false)
                        }}
                        className="text-[10px] text-red-500 hover:underline"
                      >
                        Revenir au calcul auto
                      </button>
                    )}
                  </div>

                  {isManualQuantityOpen && (
                    <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                      <div className="grid gap-1">
                        <Label htmlFor="quantity" className="text-xs text-slate-600 font-medium">Nb de parts fixe</Label>
                        <Input
                          id="quantity"
                          type="number"
                          step="any"
                          min="0"
                          placeholder="Ex: 1.5 (Laisser vide pour auto)"
                          value={formData.quantity}
                          onChange={(e) => {
                            const q = e.target.value
                            setFormData(prev => ({ ...prev, quantity: q }))
                          }}
                          className="bg-white text-xs font-mono"
                        />
                      </div>
                      <div className="grid gap-1">
                        <Label htmlFor="unit_price" className="text-xs text-slate-600 font-medium">Cours indicatif (€)</Label>
                        <Input
                          id="unit_price"
                          type="number"
                          step="any"
                          min="0"
                          placeholder="Cours indicatif..."
                          value={formData.unit_price}
                          onChange={(e) => {
                            const p = e.target.value
                            setFormData(prev => ({ ...prev, unit_price: p }))
                          }}
                          className="bg-white text-xs font-mono"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {showSecurities && (
              <div className="grid grid-cols-1 gap-4 p-3 border rounded-md bg-slate-50/50">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="aclass" className="text-xs uppercase tracking-wider font-bold text-slate-500">Classe d'actif</Label>
                    <Input 
                      id="aclass" 
                      value={formData.asset_class} 
                      onChange={(e) => setFormData({ ...formData, asset_class: e.target.value })} 
                      placeholder="Ex: Actions..." 
                      className="bg-white border-slate-200" 
                      list="classes-list"
                    />
                    <datalist id="classes-list">
                      {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                    </datalist>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="asector" className="text-xs uppercase tracking-wider font-bold text-slate-500">Secteur</Label>
                    <Input 
                      id="asector" 
                      value={formData.sector} 
                      onChange={(e) => setFormData({ ...formData, sector: e.target.value })} 
                      placeholder="Ex: Tech..." 
                      className="bg-white border-slate-200" 
                      list="sectors-list"
                    />
                    <datalist id="sectors-list">
                      {suggestions.sectors.map(s => <option key={s} value={s} />)}
                    </datalist>
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="azone" className="text-xs uppercase tracking-wider font-bold text-slate-500">Zone Géo / Pays</Label>
                  <Select value={formData.geographic_zone} onValueChange={(v) => setFormData({ ...formData, geographic_zone: v })}>
                    <SelectTrigger className="bg-white border-slate-200">
                      <SelectValue placeholder="Sélectionner un pays..." />
                    </SelectTrigger>
                    <SelectContent>
                      {COUNTRIES.map((c) => (
                        <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="account">Compte</Label>
                <Select
                  value={formData.account_id}
                  onValueChange={(v) => setFormData({ ...formData, account_id: v })}
                >
                  <SelectTrigger id="account">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map((acc) => (
                      <SelectItem key={acc.id} value={acc.id.toString()}>
                        {acc.name} ({acc.currency})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="category">Catégorie</Label>
                <Select
                  value={formData.category_id}
                  onValueChange={(v) => setFormData({ ...formData, category_id: v })}
                >
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sans catégorie</SelectItem>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id.toString()}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {formData.type === "Sortie" && selectedAccount?.type !== "investissement" && (
              <div className="grid gap-2">
                <Label htmlFor="transfer-to">Virement vers un compte (optionnel)</Label>
                <Select
                  value={formData.transfer_to_account_id}
                  onValueChange={(v) => setFormData({ ...formData, transfer_to_account_id: v })}
                >
                  <SelectTrigger id="transfer-to">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Non, c'est une dépense</SelectItem>
                    {accounts
                      .filter((acc) => acc.id.toString() !== formData.account_id)
                      .map((acc) => (
                        <SelectItem key={acc.id} value={acc.id.toString()}>
                          {acc.name} ({acc.currency})
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                {formData.transfer_to_account_id !== "none" && (
                  <p className="text-xs text-slate-500">
                    {transferToInvestment
                      ? "Chaque échéance crée la sortie, le dépôt et l'achat des parts (au cours de clôture de la date), déjà liés : renseignez le titre ci-dessous."
                      : "Chaque échéance crée la sortie et l'entrée correspondante, déjà liées : le montant n'est pas compté deux fois."}
                  </p>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="frequency">Fréquence</Label>
                <Select
                  value={formData.frequency}
                  onValueChange={(v) => setFormData({ ...formData, frequency: v })}
                >
                  <SelectTrigger id="frequency">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="weekly">Hebdomadaire</SelectItem>
                    <SelectItem value="monthly">Mensuelle</SelectItem>
                    <SelectItem value="quarterly">Trimestrielle</SelectItem>
                    <SelectItem value="yearly">Annuelle</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="day_of_month">Jour du mois</Label>
                <Input
                  id="day_of_month"
                  type="number"
                  min="1"
                  max="31"
                  value={formData.day_of_month}
                  onChange={(e) => setFormData({ ...formData, day_of_month: e.target.value })}
                />
              </div>
            </div>

            {formData.frequency === "monthly" && (
              <div className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-3">
                <button
                  type="button"
                  onClick={() => setIsIrregularSubmenuOpen(!isIrregularSubmenuOpen)}
                  className="flex items-center justify-between w-full text-left text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-slate-200/70 text-slate-600">
                      <CalendarIcon className="h-3.5 w-3.5" />
                    </span>
                    <div>
                      <span>Mois irréguliers (exclusions)</span>
                      {formData.excluded_months.length > 0 ? (
                        <span className="ml-2 text-[10px] font-bold text-amber-600 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-full">
                          {formData.excluded_months.length} exclu{formData.excluded_months.length > 1 ? "s" : ""} (
                          {formData.excluded_months.map(m => MONTHS.find(mon => mon.value === m)?.label).join(", ")})
                        </span>
                      ) : (
                        <span className="ml-2 text-[10px] text-slate-400 font-normal">Optionnel</span>
                      )}
                    </div>
                  </div>
                  <ChevronDown className={cn("h-4 w-4 text-slate-400 transition-transform duration-200", isIrregularSubmenuOpen && "rotate-180")} />
                </button>

                {isIrregularSubmenuOpen && (
                  <div className="pt-2 border-t border-slate-200/60 space-y-2">
                    <p className="text-[11px] text-slate-500">
                      Sélectionnez les mois où ce montant ne sera <strong className="font-semibold text-slate-700">pas débité</strong> (ex: non prélevé en mai et octobre).
                    </p>
                    <div className="grid grid-cols-4 sm:grid-cols-6 gap-1.5 pt-1">
                      {MONTHS.map((m) => {
                        const isExcluded = formData.excluded_months.includes(m.value)
                        return (
                          <button
                            key={m.value}
                            type="button"
                            onClick={() => {
                              setFormData(prev => ({
                                ...prev,
                                excluded_months: isExcluded
                                  ? prev.excluded_months.filter(val => val !== m.value)
                                  : [...prev.excluded_months, m.value].sort((a, b) => a - b)
                              }))
                            }}
                            className={cn(
                              "py-1.5 px-2 text-xs font-medium rounded-md border text-center transition-all",
                              isExcluded
                                ? "bg-rose-50 border-rose-300 text-rose-700 font-bold shadow-xs line-through"
                                : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                            )}
                            title={isExcluded ? `Mois exclu (${m.label})` : `Mois actif (${m.label})`}
                          >
                            {m.label}
                          </button>
                        )
                      })}
                    </div>
                    {formData.excluded_months.length > 0 && (
                      <div className="flex justify-end pt-1">
                        <button
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, excluded_months: [] }))}
                          className="text-[10px] text-slate-400 hover:text-slate-600 underline"
                        >
                          Réinitialiser les exclusions
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="grid gap-2">
              <Label>Date de début</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !formData.start_date && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {formData.start_date 
                      ? format(new Date(formData.start_date), "dd MMMM yyyy", { locale: fr })
                      : <span>Choisir une date...</span>
                    }
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={formData.start_date ? new Date(formData.start_date) : undefined}
                    onSelect={(d) => d && setFormData({ ...formData, start_date: format(d, "yyyy-MM-dd") })}
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-md bg-slate-50">
              <div className="space-y-0.5">
                <Label>Génération automatique</Label>
                <p className="text-xs text-slate-500">Créer les transactions sans intervention.</p>
              </div>
              <Checkbox 
                checked={formData.auto_generate}
                onCheckedChange={(checked: any) => setFormData({ ...formData, auto_generate: !!checked })}
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="note">Note</Label>
              <Input
                id="note"
                value={formData.note}
                onChange={(e) => setFormData({ ...formData, note: e.target.value })}
                placeholder="Note facultative..."
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsFormOpen(false)}>Annuler</Button>
            <Button onClick={handleSubmit}>Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
