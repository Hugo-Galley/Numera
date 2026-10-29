import { api } from "@/lib/api"
import { useEffect, useState } from "react"
import { Forecast } from "./types"

/** Paramètres de la prévision (horizon, épargne en plus, hypothèses) et chargement avec délai. */
export function useForecastData() {
  const [years, setYears] = useState(10)
  const [extra, setExtra] = useState(0)
  const [savingsInput, setSavingsInput] = useState("")
  const [investInput, setInvestInput] = useState("")
  const [otherInput, setOtherInput] = useState("")
  const [data, setData] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [showMethod, setShowMethod] = useState(false)
  const [showMonths, setShowMonths] = useState(false)

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ years: String(years), extra_monthly: String(extra) })
        if (savingsInput.trim() !== "" && !Number.isNaN(Number(savingsInput))) qs.set("monthly_savings", savingsInput)
        if (investInput.trim() !== "" && !Number.isNaN(Number(investInput))) qs.set("investment_return_pct", investInput)
        if (otherInput.trim() !== "" && !Number.isNaN(Number(otherInput))) qs.set("savings_return_pct", otherInput)
        const res = await api.get<Forecast>(`/analytics/wealth-forecast?${qs.toString()}`)
        if (!cancelled) {
          setData(res)
          setError(false)
        }
      } catch {
        if (!cancelled) setError(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [years, extra, savingsInput, investInput, otherInput])

  return { years, setYears, extra, setExtra, savingsInput, setSavingsInput, investInput, setInvestInput, otherInput, setOtherInput, data, setData, loading, setLoading, error, setError, showMethod, setShowMethod, showMonths, setShowMonths }
}
