import { ApiError } from "@/lib/api"
import { format, isSameDay } from "date-fns"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { useWorkTime } from "@/providers/WorkTimeProvider"
import { Account, Category, MonthSummary, SalaryConfig } from "./types"
import { getAccounts } from "@/lib/api/accounts"
import { getCategories } from "@/lib/api/classement"
import { deleteSalaryGenerateById, getSalaryConfig, getSalarySummaryById, getSalaryTelecommutingById, postSalaryConfig, postSalaryGenerateById, putSalaryConfig, putSalaryMonthsById, putSalaryTelecommutingById } from "@/lib/api/recurring"

/** Configuration du salaire, mois affiché, jours de télétravail et génération de la transaction. */
export function useSalaryData() {
  const { refresh: refreshWorkTime } = useWorkTime()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  // Chargement de la configuration : une erreur n'est PAS « pas de config » (un enregistrement écraserait la vraie)
  const [configError, setConfigError] = useState(false)
  const [monthLoadFailed, setMonthLoadFailed] = useState(false)
  const [summary, setSummary] = useState<MonthSummary | null>(null)
  const [generating, setGenerating] = useState(false)
  
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  
  const [config, setConfig] = useState<SalaryConfig>({
    salary_account_id: "",
    net_salary: 2000,
    ticket_value: 10.50,
    ticket_employee_share: 4.20,
    salary_category_id: "",
  })
  
  const [currentDate, setCurrentDate] = useState(new Date())
  const [salaryDate, setSalaryDate] = useState<Date | null>(null)
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
    setConfigError(false)
    try {
      const [accRes, catRes] = await Promise.all([
        getAccounts(),
        getCategories("?include_archived=false")
      ])
      setAccounts(accRes)
      setCategories(catRes)

      try {
        const conf = await getSalaryConfig()
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
        // Seul un 404 signifie « pas encore de configuration » ; toute autre erreur bloque l'édition
        if (!(e instanceof ApiError && e.status === 404)) throw e
      }
    } catch (error) {
      console.error("Failed to load initial data", error)
      setConfigError(true)
      toast.error("Impossible de charger la configuration du salaire")
    } finally {
      setLoading(false)
    }
  }

  async function loadMonthData(date: Date) {
    setMonthLoadFailed(false)
    try {
      const year = date.getFullYear()
      const month = date.getMonth() + 1
      
      const summary = await getSalarySummaryById(year, month)
      if (summary.salary_date) {
        setSalaryDate(new Date(summary.salary_date))
      } else {
        setSalaryDate(null)
      }
      setIsGenerated(summary.is_generated)
      setSummary(summary)
      
      const days = await getSalaryTelecommutingById(year, month)
      setTtDays(days.map((d: any) => new Date(d.date)))
    } catch (error) {
      console.error("Failed to load month data", error)
      toast.error("Impossible de charger les données du mois")
      setMonthLoadFailed(true)
      setSummary(null)
      setSalaryDate(null)
      setTtDays([])
      setIsGenerated(false)
    }
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      if (!config.salary_account_id || !config.net_salary) {
        toast.error("Veuillez remplir les champs obligatoires")
        return
      }

      const payload = {
        ...config,
        salary_account_id: Number(config.salary_account_id),
        salary_category_id: config.salary_category_id ? Number(config.salary_category_id) : null,
      }
      if (config.ticket_account_id) {
        payload.ticket_account_id = Number(config.ticket_account_id)
      }
      if (config.ticket_category_id) {
        payload.ticket_category_id = Number(config.ticket_category_id)
      }

      const res = config.id 
        ? await putSalaryConfig(payload)
        : await postSalaryConfig(payload)
      setConfig({
        ...res,
        salary_account_id: res.salary_account_id || "",
        ticket_account_id: res.ticket_account_id || "",
        salary_category_id: res.salary_category_id || "",
        ticket_category_id: res.ticket_category_id || "",
      })
      toast.success("Configuration sauvegardée")
      loadMonthData(currentDate)
      refreshWorkTime()
    } catch (error) {
      toast.error("Impossible de sauvegarder")
    } finally {
      setSaving(false)
    }
  }

  const handleToggleDay = async (date: Date) => {
    if (!config.id || isGenerated || monthLoadFailed) return

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
      await putSalaryTelecommutingById(year, month, {
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
      await putSalaryMonthsById(year, month, {
        salary_date: format(date, "yyyy-MM-dd")
      })
    } catch (error) {
      toast.error("Impossible de sauvegarder la date")
    }
  }

  const handleReset = async () => {
    try {
      const year = currentDate.getFullYear()
      const month = currentDate.getMonth() + 1
      await deleteSalaryGenerateById(year, month)
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
      const res = await postSalaryGenerateById<{ status: string }>(year, month)
      if (res?.status === "scheduled") {
        toast.success(`Salaire programmé : la transaction sera créée le ${format(new Date(salaryDate), "dd/MM/yyyy")}`)
      } else {
        toast.success("Transactions générées avec succès !")
        setIsGenerated(true)
      }
    } catch (error: any) {
      toast.error(error.message || "Erreur de génération")
    } finally {
      setGenerating(false)
    }
  }

  const nbTickets = summary?.tt_days_count ?? 0

  return { loading, setLoading, saving, setSaving, configError, setConfigError, monthLoadFailed, setMonthLoadFailed, summary, setSummary, generating, setGenerating, accounts, setAccounts, categories, setCategories, config, setConfig, currentDate, setCurrentDate, salaryDate, setSalaryDate, ttDays, setTtDays, isGenerated, setIsGenerated, loadInitialData, loadMonthData, handleSaveConfig, handleToggleDay, handleSalaryDateChange, handleReset, handleGenerate, nbTickets }
}
