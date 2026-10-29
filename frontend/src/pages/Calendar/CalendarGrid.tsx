import { Card } from "@/components/ui/card"
import { Clock } from "lucide-react"
import { cn, formatCurrency } from "@/lib/utils"
import type { CalendarCtx } from "./useCalendar"

/** Grille du mois (événements et soldes par jour). */
export function CalendarGrid({ ctx }: { ctx: CalendarCtx }) {
  const { calendarDays, getBalanceForDay, getEventsForDay, handleDayClick, isPrivacyMode, month, year } = ctx
  return (
    <>
      <Card className="border-slate-200 shadow-sm overflow-hidden">
        <div className="grid grid-cols-7 bg-slate-50 border-b text-center py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          {["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"].map(d => (
            <div key={d}>{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7 auto-rows-[56px] md:auto-rows-[minmax(100px,1fr)]">
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
                  "p-1 md:p-2 border-b border-r border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer flex flex-col items-center md:items-stretch gap-0.5 md:gap-1 min-w-0",
                  isToday && "bg-blue-50/30"
                )}
              >
                <div className="flex items-center justify-center md:justify-between w-full">
                  <span className={cn(
                    "text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full",
                    isToday ? "bg-blue-600 text-white" : "text-slate-400"
                  )}>
                    {day}
                  </span>
                  {balance !== null && balance !== undefined && !isPrivacyMode && (
                    <span className={cn(
                      "hidden md:inline text-[10px] font-medium",
                      balance < 0 ? "text-red-500" : "text-slate-400"
                    )}>
                      {formatCurrency(balance, "EUR")}
                    </span>
                  )}
                </div>

                {events.length > 0 && (
                  <div className="flex items-center gap-0.5 md:hidden">
                    {events.slice(0, 3).map((ev) => (
                      <span
                        key={ev.id}
                        className={cn(
                          "h-1.5 w-1.5 rounded-full",
                          ev.type === "Sortie" || ev.type === "retrait"
                            ? (ev.is_projected ? "bg-amber-400" : "bg-slate-500")
                            : "bg-emerald-500"
                        )}
                      />
                    ))}
                    {events.length > 3 && <span className="text-[9px] leading-none text-slate-400">+</span>}
                  </div>
                )}
                <div className="hidden md:flex flex-col gap-0.5 overflow-hidden">
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
    </>
  )
}
