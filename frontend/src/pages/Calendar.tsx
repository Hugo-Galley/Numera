import { useState, useEffect } from "react"
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar as CalendarIcon,
  Info,
  Clock,
  ArrowUpCircle,
  ArrowDownCircle,
  Plus,
  CheckCircle2
} from "lucide-react"
import { cn, formatCurrency } from "@/lib/utils"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useUI } from "@/providers/UIProvider"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Link } from "react-router-dom"
import { toast } from "sonner"

interface CalendarEvent {
  id: string | number
  date: string
  name: string
  amount: number
  type: string
  category_id: number | null
  is_projected: boolean
  currency: string
  recurring_id?: number
}

interface DailyBalance {
  date: string
  balance: number
}

interface CalendarData {
  month: number
  year: number
  events: CalendarEvent[]
  daily_balances: DailyBalance[]
}

interface Account {
  id: number
  name: string
  currency: string
  type: string
}

export default function Calendar() {
  const { isPrivacyMode } = useUI()
  const [date, setDate] = useState(new Date())
  const [data, setData] = useState<CalendarData | null>(null)
  const [loading, setLoading] = useState(true)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>("all")
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [isDayDetailOpen, setIsDayDetailOpen] = useState(false)

  const month = date.getMonth() + 1
  const year = date.getFullYear()

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const accs = await api.get<Account[]>("/accounts")
        setAccounts(accs)
      } catch (error) {
        console.error("Failed to fetch accounts", error)
      }
    }
    fetchAccounts()
  }, [])

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const query = `month=${month}&year=${year}${selectedAccountId !== "all" ? `&account_id=${selectedAccountId}` : ""}`
        const res = await api.get<CalendarData>(`/analytics/calendar?${query}`)
        setData(res)
      } catch (error) {
        console.error("Failed to fetch calendar data", error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [month, year, selectedAccountId])

  const nextMonth = () => setDate(new Date(year, month, 1))
  const prevMonth = () => setDate(new Date(year, month - 2, 1))

  const firstDayOfMonth = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()
  
  // Adjust for Monday start
  const startingDay = firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1
  
  const calendarDays = []
  for (let i = 0; i < startingDay; i++) {
    calendarDays.push(null)
  }
  for (let i = 1; i <= daysInMonth; i++) {
    calendarDays.push(i)
  }

  const getEventsForDay = (day: number) => {
    if (!data) return []
    const dayStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    return data.events.filter(e => e.date.startsWith(dayStr))
  }

  const getBalanceForDay = (day: number) => {
    if (!data || !data.daily_balances.length) return null
    const dayStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    return data.daily_balances.find(b => b.date === dayStr)?.balance
  }

  const handleDayClick = (day: number) => {
    const dayStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    setSelectedDay(dayStr)
    setIsDayDetailOpen(true)
  }

  const handleValidate = async (ev: CalendarEvent) => {
    if (!ev.recurring_id || !selectedDay) return
    
    try {
      // Find the recurring transaction details
      const recurringTx = await api.get<any>(`/recurring-transactions/${ev.recurring_id}`)
      const account = accounts.find(a => a.id === recurringTx.account_id)
      
      if (!account) {
        toast.error("Compte non trouvé")
        return
      }

      const isInvAccount = account.type === "investissement"
      const isInvType = ["versement", "retrait", "dividende"].includes(ev.type.toLowerCase())

      if (isInvAccount && isInvType) {
        await api.post("/investment-transactions", {
          account_id: account.id,
          date: new Date(ev.date).toISOString(),
          type: ev.type.toLowerCase(),
          amount: ev.amount,
          currency: ev.currency,
          note: recurringTx.note || recurringTx.name,
          asset_class: recurringTx.asset_class,
          sector: recurringTx.sector,
          geographic_zone: recurringTx.geographic_zone
        })
      } else {
        await api.post("/transactions", {
          account_id: account.id,
          date: new Date(ev.date).toISOString(),
          type: ev.type,
          merchant: ev.name,
          amount: ev.amount,
          currency: ev.currency,
          category_id: ev.category_id,
          is_recurring: true,
          recurring_transaction_id: ev.recurring_id
        })
      }
      
      toast.success("Transaction validée !")
      // Refresh data
      const query = `month=${month}&year=${year}${selectedAccountId !== "all" ? `&account_id=${selectedAccountId}` : ""}`
      const res = await api.get<CalendarData>(`/analytics/calendar?${query}`)
      setData(res)
    } catch (error) {
      console.error("Failed to validate transaction", error)
      toast.error("Erreur lors de la validation")
    }
  }

  const selectedDayEvents = selectedDay 
    ? data?.events.filter(e => e.date.startsWith(selectedDay)) || []
    : []

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Calendrier Financier</h1>
          <p className="text-slate-500">Visualisez vos flux réels et prévus sur le mois.</p>
        </div>
        
        <div className="flex items-center gap-2">
          <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
            <SelectTrigger className="w-[180px] bg-white">
              <SelectValue placeholder="Tous les comptes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les comptes</SelectItem>
              {accounts.map(acc => (
                <SelectItem key={acc.id} value={acc.id.toString()}>{acc.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <div className="flex items-center bg-white border rounded-md p-1 shadow-sm">
            <Button variant="ghost" size="icon" onClick={prevMonth} className="h-8 w-8">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="px-4 py-1 text-sm font-medium min-w-[140px] text-center capitalize">
              {date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
            </div>
            <Button variant="ghost" size="icon" onClick={nextMonth} className="h-8 w-8">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <Card className="border-slate-200 shadow-sm overflow-hidden">
        <div className="grid grid-cols-7 bg-slate-50 border-b text-center py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          {["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"].map(d => (
            <div key={d}>{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7 auto-rows-[minmax(100px,1fr)]">
          {calendarDays.map((day, idx) => {
            if (day === null) {
              return <div key={`empty-${idx}`} className="bg-slate-50/30 border-b border-r border-slate-100" />
            }
            
            const events = getEventsForDay(day)
            const balance = getBalanceForDay(day)
            const isToday = new Date().toDateString() === new Date(year, month - 1, day).toDateString()
            
            return (
              <div 
                key={day} 
                onClick={() => handleDayClick(day)}
                className={cn(
                  "p-2 border-b border-r border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer flex flex-col gap-1",
                  isToday && "bg-blue-50/30"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className={cn(
                    "text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full",
                    isToday ? "bg-blue-600 text-white" : "text-slate-400"
                  )}>
                    {day}
                  </span>
                  {balance !== null && balance !== undefined && !isPrivacyMode && (
                    <span className={cn(
                      "text-[10px] font-medium",
                      balance < 0 ? "text-red-500" : "text-slate-400"
                    )}>
                      {formatCurrency(balance, "EUR")}
                    </span>
                  )}
                </div>
                
                <div className="flex flex-col gap-0.5 overflow-hidden">
                  {events.slice(0, 3).map((ev, i) => {
                    const isEvNegative = ev.type === "Sortie" || ev.type === "retrait"
                    return (
                      <div 
                        key={ev.id} 
                        className={cn(
                          "text-[10px] px-1 py-0.5 rounded truncate flex items-center gap-1",
                          isEvNegative
                            ? (ev.is_projected ? "bg-amber-50 text-amber-700 border border-amber-100/50" : "bg-slate-100 text-slate-700")
                            : (ev.is_projected ? "bg-emerald-50 text-emerald-700 border border-emerald-100/50" : "bg-emerald-100 text-emerald-800")
                        )}
                      >
                        {ev.is_projected && <Clock className="h-2 w-2 flex-shrink-0" />}
                        <span className="truncate">{ev.name}</span>
                      </div>
                    )
                  })}
                  {events.length > 3 && (
                    <div className="text-[9px] text-slate-400 pl-1 font-medium">
                      + {events.length - 3} autres
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Prochaines Échéances</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data?.events.filter(e => e.is_projected).slice(0, 5).map(ev => {
                const isEvNegative = ev.type === "Sortie" || ev.type === "retrait"
                return (
                  <div key={ev.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-amber-500" />
                      <span className="font-medium truncate max-w-[120px]">{ev.name}</span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className={cn("font-bold", isEvNegative ? "text-slate-900" : "text-emerald-600")}>
                        {isEvNegative ? "-" : "+"}{isPrivacyMode ? "***" : formatCurrency(ev.amount, ev.currency)}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(ev.date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
                      </span>
                    </div>
                  </div>
                )
              })}
              {data?.events.filter(e => e.is_projected).length === 0 && (
                <p className="text-xs text-slate-400 text-center py-4">Aucune échéance prévue</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Légende & Infos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-slate-100 border border-slate-200" />
                <span>Transaction réelle (Passé/Présent)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-amber-50 border border-amber-200" />
                <span>Prévu / Récurrent (Futur)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-600" />
                <span>Aujourd'hui</span>
              </div>
              <div className="mt-4 p-2 bg-slate-50 rounded border border-slate-100 flex gap-2">
                <Info className="h-4 w-4 text-slate-400 flex-shrink-0" />
                <p className="text-slate-500 leading-tight">
                  Les soldes quotidiens incluent les transactions réelles passées et les projections futures basées sur vos abonnements et revenus récurrents.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 flex flex-col justify-center items-center p-6 text-center">
          <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
            <Plus className="h-6 w-6 text-slate-600" />
          </div>
          <h3 className="font-bold text-slate-900">Ajouter une récurrence</h3>
          <p className="text-sm text-slate-500 mt-1 mb-4">
            Gérez vos revenus et charges fixes pour des projections plus précises.
          </p>
          <Button variant="outline" size="sm" className="w-full" asChild>
            <Link to="/recurring">Accéder aux récurrences</Link>
          </Button>
        </Card>
      </div>

      <Dialog open={isDayDetailOpen} onOpenChange={setIsDayDetailOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5 text-slate-400" />
              {selectedDay && new Date(selectedDay).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </DialogTitle>
            <DialogDescription>
              Flux financiers pour cette journée
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {selectedDayEvents.length > 0 ? (
              <div className="space-y-3">
                {selectedDayEvents.map((ev) => {
                  const isEvNegative = ev.type === "Sortie" || ev.type === "retrait"
                  return (
                    <div key={ev.id} className="flex items-center justify-between p-2 rounded-lg border border-slate-100 bg-slate-50/50">
                      <div className="flex items-center gap-3">
                        {isEvNegative ? (
                          <ArrowDownCircle className="h-8 w-8 text-slate-400" />
                        ) : (
                          <ArrowUpCircle className="h-8 w-8 text-emerald-500" />
                        )}
                        <div>
                          <p className="text-sm font-bold text-slate-900">{ev.name}</p>
                          <div className="flex items-center gap-1.5">
                            {ev.is_projected && <Badge variant="secondary" className="h-4 text-[9px] px-1 bg-amber-100 text-amber-700 hover:bg-amber-100 border-none">PRÉVU</Badge>}
                            <span className="text-[10px] text-slate-500 uppercase font-medium tracking-wider">{ev.type}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <p className={cn(
                          "text-sm font-bold",
                          isEvNegative ? "text-slate-900" : "text-emerald-600"
                        )}>
                          {isEvNegative ? "-" : "+"}{isPrivacyMode ? "***" : formatCurrency(ev.amount, ev.currency)}
                        </p>
                        {ev.is_projected && ev.recurring_id && (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="h-6 text-[10px] gap-1 px-1.5 hover:bg-emerald-50 hover:text-emerald-700"
                            onClick={() => handleValidate(ev)}
                          >
                            <CheckCircle2 className="h-3 w-3" />
                            Valider
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-400 italic">
                Aucune transaction ce jour
              </div>
            )}
            
            {selectedDay && (
              <div className="pt-4 border-t flex items-center justify-between text-sm">
                <span className="text-slate-500 font-medium">Solde estimé fin de journée</span>
                <span className={cn(
                  "font-bold",
                  (getBalanceForDay(new Date(selectedDay).getDate()) || 0) < 0 ? "text-red-600" : "text-slate-900"
                )}>
                  {isPrivacyMode ? "***" : formatCurrency(getBalanceForDay(new Date(selectedDay).getDate()) || 0, "EUR")}
                </span>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
