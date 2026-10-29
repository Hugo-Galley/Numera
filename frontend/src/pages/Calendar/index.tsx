import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { ErrorState } from "@/components/layout/ErrorState"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useCalendar } from "./useCalendar"
import { CalendarGrid } from "./CalendarGrid"
import { CalendarSummary } from "./CalendarSummary"
import { DayDetailDialog } from "./DayDetailDialog"

export default function Calendar({ embedded = false }: { embedded?: boolean }) {
  const ctx = useCalendar(embedded)
  const { accounts, date, loadFailed, month, nextMonth, prevMonth, selectedAccountId, setReloadToken, setSelectedAccountId, year } = ctx
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 md:gap-4">
        {!embedded && (
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Calendrier Financier</h1>
            <p className="text-slate-500">Visualisez vos flux réels et prévus sur le mois.</p>
          </div>
        )}
        
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
            <SelectTrigger className="h-10 w-full bg-white sm:w-[180px]">
              <SelectValue placeholder="Tous les comptes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les comptes</SelectItem>
              {accounts.map(acc => (
                <SelectItem key={acc.id} value={acc.id.toString()}>{acc.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <div className="flex items-center justify-between bg-white border rounded-md p-1 shadow-sm">
            <Button variant="ghost" size="icon" onClick={prevMonth} className="h-10 w-10 md:h-8 md:w-8" aria-label="Mois précédent">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="px-4 py-1 text-sm font-medium flex-1 md:flex-none md:min-w-[140px] text-center capitalize">
              {date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
            </div>
            <Button variant="ghost" size="icon" onClick={nextMonth} className="h-10 w-10 md:h-8 md:w-8" aria-label="Mois suivant">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {loadFailed && (
        <ErrorState message="Le calendrier n'a pas pu être chargé." onRetry={() => setReloadToken(t => t + 1)} />
      )}
      <CalendarGrid ctx={ctx} />

      <CalendarSummary ctx={ctx} />

      <DayDetailDialog ctx={ctx} />
    </div>
  )
}
