import { useState, useEffect } from "react"
import { format, isSameDay } from "date-fns"
import { fr } from "date-fns/locale"
import { Save, Wallet, Download, CheckCircle2, Building, Utensils } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { TelecommutingCalendar } from "./TelecommutingCalendar"

interface SalaryConfig {
  id?: number
  salary_account_id: number | ""
  ticket_account_id: number | ""
  net_salary: number
  ticket_value: number
  ticket_employee_share: number
  salary_category_id: number | ""
  ticket_category_id: number | ""
}

interface Account {
  id: number
  name: string
  type: string
}

interface Category {
  id: number
  name: string
}

export function SalaryManager() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  
  const [config, setConfig] = useState<SalaryConfig>({
    salary_account_id: "",
    ticket_account_id: "",
    net_salary: 2000,
    ticket_value: 10.50,
    ticket_employee_share: 4.20,
    salary_category_id: "",
    ticket_category_id: "",
  })
  
  const [currentDate, setCurrentDate] = useState(new Date())
  const [salaryDate, setSalaryDate] = useState<Date | null>(null)
  const [ticketDate, setTicketDate] = useState<Date | null>(null)
  const [ttDays, setTtDays] = useState<Date[]>([])
  const [isGenerated, setIsGenerated] = useState(false)

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    if (config.id) {
      loadMonthData(currentDate)
    }
  }, [currentDate, config.id])

  async function loadInitialData() {
    try {
      const [accRes, catRes] = await Promise.all([
        api.get("/accounts"),
        api.get("/categories")
      ])
      setAccounts(accRes)
      setCategories(catRes)

      try {
        const conf = await api.get("/salary/config")
        if (conf) {
          setConfig({
            ...conf,
            salary_account_id: conf.salary_account_id || "",
            ticket_account_id: conf.ticket_account_id || "",
            salary_category_id: conf.salary_category_id || "",
            ticket_category_id: conf.ticket_category_id || "",
          })
        }
      } catch (e) {
        // No config yet, normal
      }
    } catch (error) {
      console.error("Failed to load initial data", error)
    } finally {
      setLoading(false)
    }
  }

  async function loadMonthData(date: Date) {
    try {
      const year = date.getFullYear()
      const month = date.getMonth() + 1
      
      const summary = await api.get(`/salary/summary/${year}/${month}`)
      if (summary.salary_date) {
        setSalaryDate(new Date(summary.salary_date))
      } else {
        setSalaryDate(null)
      }
      if (summary.ticket_date) {
        setTicketDate(new Date(summary.ticket_date))
      } else {
        setTicketDate(null)
      }
      setIsGenerated(summary.is_generated)
      
      const days = await api.get(`/salary/telecommuting/${year}/${month}`)
      setTtDays(days.map((d: any) => new Date(d.date)))
    } catch (error) {
      console.error("Failed to load month data", error)
      setSalaryDate(null)
      setTicketDate(null)
      setTtDays([])
      setIsGenerated(false)
    }
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      if (!config.salary_account_id || !config.ticket_account_id || !config.net_salary) {
        toast.error("Veuillez remplir les champs obligatoires")
        return
      }

      const payload = {
        ...config,
        salary_account_id: Number(config.salary_account_id),
        ticket_account_id: Number(config.ticket_account_id),
        salary_category_id: config.salary_category_id ? Number(config.salary_category_id) : null,
        ticket_category_id: config.ticket_category_id ? Number(config.ticket_category_id) : null,
      }

      const res = config.id 
        ? await api.put("/salary/config", payload)
        : await api.post("/salary/config", payload)
      setConfig({
        ...res,
        salary_account_id: res.salary_account_id || "",
        ticket_account_id: res.ticket_account_id || "",
        salary_category_id: res.salary_category_id || "",
        ticket_category_id: res.ticket_category_id || "",
      })
      toast.success("Configuration sauvegardée")
      loadMonthData(currentDate)
    } catch (error) {
      toast.error("Impossible de sauvegarder")
    } finally {
      setSaving(false)
    }
  }

  const handleToggleDay = async (date: Date) => {
    if (!config.id || isGenerated) return

    const year = currentDate.getFullYear()
    const month = currentDate.getMonth() + 1
    
    let newDays = [...ttDays]
    const exists = newDays.findIndex(d => isSameDay(d, date))
    
    if (exists >= 0) {
      newDays.splice(exists, 1)
    } else {
      newDays.push(date)
    }
    
    setTtDays(newDays)
    
    try {
      await api.put(`/salary/telecommuting/${year}/${month}`, {
        dates: newDays.map(d => format(d, "yyyy-MM-dd"))
      })
      loadMonthData(currentDate)
    } catch (error) {
      toast.error("Impossible de sauvegarder le jour")
      loadMonthData(currentDate)
    }
  }

  const handleSalaryDateChange = async (date: Date) => {
    if (!config.id || isGenerated) return
    
    setSalaryDate(date)
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth() + 1
    
    try {
      await api.put(`/salary/months/${year}/${month}`, {
        salary_date: format(date, "yyyy-MM-dd"),
        ticket_date: ticketDate ? format(ticketDate, "yyyy-MM-dd") : null
      })
    } catch (error) {
      toast.error("Impossible de sauvegarder la date")
    }
  }

  const handleTicketDateChange = async (date: Date) => {
    if (!config.id || isGenerated) return
    
    if (!salaryDate) {
      toast.error("Veuillez d'abord définir la date du salaire")
      return
    }
    
    setTicketDate(date)
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth() + 1
    
    try {
      await api.put(`/salary/months/${year}/${month}`, {
        salary_date: salaryDate ? format(salaryDate, "yyyy-MM-dd") : null,
        ticket_date: format(date, "yyyy-MM-dd")
      })
    } catch (error) {
      toast.error("Impossible de sauvegarder la date")
    }
  }

  const handleReset = async () => {
    try {
      const year = currentDate.getFullYear()
      const month = currentDate.getMonth() + 1
      await api.delete(`/salary/generate/${year}/${month}`)
      toast.success("Mois réinitialisé !")
      setIsGenerated(false)
    } catch (error: any) {
      toast.error(error.message || "Erreur de réinitialisation")
    }
  }

  const handleGenerate = async () => {
    if (!salaryDate) {
      toast.error("Veuillez définir une date de versement")
      return
    }
    
    setGenerating(true)
    try {
      const year = currentDate.getFullYear()
      const month = currentDate.getMonth() + 1
      await api.post(`/salary/generate/${year}/${month}`)
      toast.success("Transactions générées avec succès !")
      setIsGenerated(true)
    } catch (error: any) {
      toast.error(error.message || "Erreur de génération")
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return <div className="flex justify-center p-8"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>
  }

  const nbTickets = ttDays.length
  const deduction = nbTickets * config.ticket_employee_share
  const realSalary = config.net_salary - deduction
  const creditTR = nbTickets * config.ticket_value

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building className="h-5 w-5" />
            Configuration Salaire & Avantages
          </CardTitle>
          <CardDescription>
            Définissez votre salaire net après primes et les comptes cibles pour automatiser vos transactions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
            <div className="space-y-2">
              <Label>Salaire net après primes (€)</Label>
              <Input 
                type="number" 
                value={config.net_salary} 
                onChange={e => setConfig({...config, net_salary: parseFloat(e.target.value) || 0})}
              />
            </div>
            <div className="space-y-2">
              <Label>Valeur ticket restaurant (€)</Label>
              <Input 
                type="number" 
                step="0.01"
                value={config.ticket_value} 
                onChange={e => setConfig({...config, ticket_value: parseFloat(e.target.value) || 0})}
              />
            </div>
            <div className="space-y-2">
              <Label>Part salarié TR (€)</Label>
              <Input 
                type="number" 
                step="0.01"
                value={config.ticket_employee_share} 
                onChange={e => setConfig({...config, ticket_employee_share: parseFloat(e.target.value) || 0})}
              />
            </div>

            <div className="space-y-2">
              <Label>Compte de versement Salaire *</Label>
              <Select value={config.salary_account_id.toString()} onValueChange={v => setConfig({...config, salary_account_id: v})}>
                <SelectTrigger><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {accounts.map(a => <SelectItem key={a.id} value={a.id.toString()}>{a.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Compte ou Carte TR *</Label>
              <Select value={config.ticket_account_id.toString()} onValueChange={v => setConfig({...config, ticket_account_id: v})}>
                <SelectTrigger><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {accounts.map(a => <SelectItem key={a.id} value={a.id.toString()}>{a.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Catégorie Salaire</Label>
              <Select value={config.salary_category_id ? config.salary_category_id.toString() : "none"} onValueChange={v => setConfig({...config, salary_category_id: v === "none" ? "" : parseInt(v)})}>
                <SelectTrigger><SelectValue placeholder="Aucune catégorie" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Aucune catégorie</SelectItem>
                  {categories.map(c => <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Catégorie Tickets Restaurant</Label>
              <Select value={config.ticket_category_id ? config.ticket_category_id.toString() : "none"} onValueChange={v => setConfig({...config, ticket_category_id: v === "none" ? "" : parseInt(v)})}>
                <SelectTrigger><SelectValue placeholder="Aucune catégorie" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Aucune catégorie</SelectItem>
                  {categories.map(c => <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-end">
              <Button onClick={handleSaveConfig} disabled={saving} className="w-full">
                {saving ? "Enregistrement..." : <><Save className="mr-2 h-4 w-4" /> Sauvegarder</>}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {config.id && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <TelecommutingCalendar 
              currentDate={currentDate}
              onDateChange={setCurrentDate}
              salaryDate={salaryDate}
              onSalaryDateChange={handleSalaryDateChange}
              ticketDate={ticketDate}
              onTicketDateChange={handleTicketDateChange}
              ttDays={ttDays}
              onToggleDay={handleToggleDay}
            />
          </div>
          
          <div className="lg:col-span-1">
            <Card className="h-full flex flex-col shadow-md">
              <CardHeader className="border-b pb-4">
                <CardTitle className="text-lg flex justify-between items-center">
                  <span className="flex items-center gap-2">
                    <Wallet className="h-5 w-5 text-primary" />
                    Résumé du mois
                  </span>
                  <span className="text-sm font-medium text-muted-foreground">
                    {format(currentDate, "MMMM yyyy", { locale: fr })}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 flex-1 flex flex-col">
                <div className="space-y-6 flex-1">
                  
                  {/* Banque */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                      Reçu en Banque
                    </h3>
                    <div className="bg-muted/50 border rounded-xl p-4 text-sm shadow-inner">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-muted-foreground">Salaire net après primes</span>
                        <span className="font-medium">{config.net_salary.toFixed(2)} €</span>
                      </div>
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-muted-foreground">Déduction TR ({nbTickets} × {config.ticket_employee_share.toFixed(2)}€)</span>
                        <span className="text-destructive font-medium">- {deduction.toFixed(2)} €</span>
                      </div>
                      <div className="border-t pt-3 flex justify-between items-center">
                        <span className="font-bold">Total versé</span>
                        <span className="font-black text-xl text-emerald-600 dark:text-emerald-400">{realSalary.toFixed(2)} €</span>
                      </div>
                    </div>
                  </div>

                  {/* TR */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                      Carte Titres-Restaurant
                    </h3>
                    <div className="bg-muted/50 border rounded-xl p-4 text-sm shadow-inner">
                      <div className="flex justify-between items-center">
                        <span className="text-muted-foreground">Tickets crédités ({nbTickets} × {config.ticket_value.toFixed(2)}€)</span>
                        <span className="font-black text-xl text-amber-500 dark:text-amber-400">+ {creditTR.toFixed(2)} €</span>
                      </div>
                    </div>
                  </div>
                  
                </div>

                <div className="mt-8 pt-6 border-t">
                  {isGenerated ? (
                    <div className="flex flex-col gap-3">
                      <div className="bg-emerald-100 border border-emerald-200 text-emerald-700 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-400 p-4 rounded-xl flex items-center justify-center gap-2 font-medium shadow-sm">
                        <CheckCircle2 className="h-5 w-5" />
                        Mois validé (Planifié)
                      </div>
                      <Button variant="outline" className="w-full" onClick={handleReset}>
                        Réinitialiser ce mois
                      </Button>
                    </div>
                  ) : (
                    <Button 
                      className="w-full h-12 text-base font-bold shadow-lg transition-transform hover:scale-[1.02]" 
                      onClick={handleGenerate}
                      disabled={generating || !salaryDate}
                    >
                      {generating ? "Génération..." : <><Download className="mr-2 h-5 w-5" /> Générer les transactions</>}
                    </Button>
                  )}
                  {!salaryDate && !isGenerated && (
                    <p className="text-xs text-center text-slate-400 mt-3 font-medium">
                      Veuillez définir une date de versement dans le calendrier
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
