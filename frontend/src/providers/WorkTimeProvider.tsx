import i18n from "i18next"
import { toast } from "sonner"
import React, { createContext, useCallback, useContext, useEffect, useState } from "react"
import { resetApiCache } from "@/lib/apiCache"
import { getSalaryWorkTime } from "@/lib/api/recurring"

export interface WorkTime {
  configured: boolean
  net_salary: number | null
  work_days_per_year: number
  work_hours_per_day: number
  hours_per_month: number
  hourly_rate: number | null
}

interface WorkTimeContextType {
  workTime: WorkTime | null
  refresh: () => Promise<void>
}

const WorkTimeContext = createContext<WorkTimeContextType | undefined>(undefined)

export function WorkTimeProvider({ children }: { children: React.ReactNode }) {
  const [workTime, setWorkTime] = useState<WorkTime | null>(null)

  const load = useCallback(async () => {
    try {
      setWorkTime(await getSalaryWorkTime<WorkTime>())
    } catch (error) {
      console.error("Erreur lors du chargement du taux horaire", error)
      toast.error(i18n.t("errors.workRateFailed", { ns: "common" }))
    }
  }, [])

  // Rechargement demandé (après un changement de réglage) : on contourne le cache de lecture
  const refresh = useCallback(async () => {
    resetApiCache()
    await load()
  }, [load])

  useEffect(() => {
    load()
  }, [load])

  return <WorkTimeContext.Provider value={{ workTime, refresh }}>{children}</WorkTimeContext.Provider>
}

export function useWorkTime() {
  const context = useContext(WorkTimeContext)
  if (context === undefined) {
    throw new Error("useWorkTime must be used within a WorkTimeProvider")
  }
  return context
}
