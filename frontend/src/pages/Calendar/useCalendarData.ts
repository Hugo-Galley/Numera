import { toNaiveLocal } from "@/lib/dates"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { useSubmit } from "@/hooks/useSubmit"
import { useUI } from "@/providers/UIProvider"
import { Account, CalendarData, CalendarEvent } from "./types"
import { getAccounts } from "@/lib/api/accounts"
import { getAnalyticsCalendar } from "@/lib/api/analytics"
import { postInvestmentTransactions } from "@/lib/api/investments"
import { getRecurringTransactionsById } from "@/lib/api/recurring"
import { postTransactions } from "@/lib/api/transactions"

/** Mois affiché, chargement des événements et soldes, sélection d'un jour et validation d'une échéance. */
export function useCalendarData(p: { embedded: boolean }) {
  const { embedded } = p
  const { isPrivacyMode } = useUI()
  const [date, setDate] = useState(new Date())
  const [data, setData] = useState<CalendarData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>("all")
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [isDayDetailOpen, setIsDayDetailOpen] = useState(false)

  const month = date.getMonth() + 1
  const year = date.getFullYear()

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const accs = await getAccounts<Account[]>()
        setAccounts(accs)
      } catch (error) {
        console.error("Failed to fetch accounts", error)
        toast.error("Impossible de charger les comptes")
      }
    }
    fetchAccounts()
  }, [])

  useEffect(() => {
    let cancelled = false
    const fetchData = async () => {
      setLoading(true)
      setLoadFailed(false)
      setData(null)
      try {
        const query = `month=${month}&year=${year}${selectedAccountId !== "all" ? `&account_id=${selectedAccountId}` : ""}`
        const res = await getAnalyticsCalendar<CalendarData>(`?${query}`)
        if (!cancelled) setData(res)
      } catch (error) {
        console.error("Failed to fetch calendar data", error)
        if (!cancelled) {
          setLoadFailed(true)
          toast.error("Impossible de charger le calendrier")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => {
      cancelled = true
    }
  }, [month, year, selectedAccountId, reloadToken])

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

  const [handleValidate, validating] = useSubmit(async (ev: CalendarEvent) => {
    if (!ev.recurring_id || !selectedDay) return
    
    try {
      // Find the recurring transaction details
      const recurringTx = await getRecurringTransactionsById<any>(ev.recurring_id)
      const account = accounts.find(a => a.id === recurringTx.account_id)
      
      if (!account) {
        toast.error("Compte non trouvé")
        return
      }

      const isInvAccount = account.type === "investissement" || account.type === "assurance_vie" || !!recurringTx.ticker
      const isInvType = ["versement", "retrait", "dividende", "achat", "vente", "sortie", "entree"].includes(ev.type.toLowerCase())

      if (isInvAccount && isInvType) {
        let invType = ev.type.toLowerCase()
        if (invType === "sortie" || invType === "achat") invType = "versement"
        else if (invType === "entree" || invType === "vente") invType = "retrait"

        await postInvestmentTransactions({
          account_id: account.id,
          date: toNaiveLocal(ev.date),
          type: invType,
          amount: ev.amount,
          currency: ev.currency,
          note: recurringTx.note || recurringTx.name,
          asset_class: recurringTx.asset_class,
          sector: recurringTx.sector,
          geographic_zone: recurringTx.geographic_zone,
          ticker: recurringTx.ticker,
          isin: recurringTx.isin,
          quantity: recurringTx.quantity,
          unit_price: recurringTx.unit_price,
          etf_profile_id: recurringTx.etf_profile_id,
        })
      } else {
        await postTransactions({
          account_id: account.id,
          date: toNaiveLocal(ev.date),
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
      const res = await getAnalyticsCalendar<CalendarData>(`?${query}`)
      setData(res)
    } catch (error) {
      console.error("Failed to validate transaction", error)
      toast.error("Erreur lors de la validation")
    }
  })

  const selectedDayEvents = selectedDay 
    ? data?.events.filter(e => e.date.startsWith(selectedDay)) || []
    : []

  return { isPrivacyMode, date, setDate, data, setData, loading, setLoading, loadFailed, setLoadFailed, reloadToken, setReloadToken, accounts, setAccounts, selectedAccountId, setSelectedAccountId, selectedDay, setSelectedDay, isDayDetailOpen, setIsDayDetailOpen, month, year, nextMonth, prevMonth, firstDayOfMonth, daysInMonth, startingDay, calendarDays, getEventsForDay, getBalanceForDay, handleDayClick, handleValidate, validating, selectedDayEvents }
}
