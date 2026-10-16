import React, { createContext, useCallback, useContext, useEffect, useState } from "react"
import { api } from "@/lib/api"

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

  const refresh = useCallback(async () => {
    try {
      setWorkTime(await api.get<WorkTime>("/salary/work-time"))
    } catch (error) {
      console.error("Erreur lors du chargement du taux horaire", error)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return <WorkTimeContext.Provider value={{ workTime, refresh }}>{children}</WorkTimeContext.Provider>
}

export function useWorkTime() {
  const context = useContext(WorkTimeContext)
  if (context === undefined) {
    throw new Error("useWorkTime must be used within a WorkTimeProvider")
  }
  return context
}
