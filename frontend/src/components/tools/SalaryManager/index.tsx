import { ErrorState } from "@/components/layout/ErrorState"
import { TelecommutingCalendar } from "../TelecommutingCalendar"
import { WorkTimeSettings } from "../WorkTimeSettings"
import { useSalaryManager } from "./useSalaryManager"
import { SalaryConfigCard } from "./SalaryConfigCard"
import { MonthSummaryPanel } from "./MonthSummaryPanel"

export function SalaryManager() {
  const ctx = useSalaryManager()
  const { config, configError, currentDate, handleSalaryDateChange, handleToggleDay, loadInitialData, loading, salaryDate, setCurrentDate, ttDays } = ctx
  if (loading) {
    return <div className="flex justify-center p-8"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>
  }

  if (configError) {
    return <ErrorState message="La configuration du salaire n'a pas pu être chargée. Rien n'est modifié." onRetry={loadInitialData} />
  }

  // Montants calculés par le backend (core/salary.py) : jamais recalculés ici
  return (
    <div className="space-y-6">
      <SalaryConfigCard ctx={ctx} />

      {config.id && <WorkTimeSettings />}

      {config.id && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
          <div className="lg:col-span-2 min-w-0">
            <TelecommutingCalendar 
              currentDate={currentDate}
              onDateChange={setCurrentDate}
              salaryDate={salaryDate}
              onSalaryDateChange={handleSalaryDateChange}
              ttDays={ttDays}
              onToggleDay={handleToggleDay}
            />
          </div>
          
            <MonthSummaryPanel ctx={ctx} />
        </div>
      )}
    </div>
  )
}
