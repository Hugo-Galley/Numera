import { Button } from "@/components/ui/button"
import { Calendar, Filter, Plus } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { AccountDetailView } from "./useAccountDetail"

/** Barre de filtres de la liste (recherche, période, type, catégorie, marchand, tags). */
export function FilterBar({ ctx }: { ctx: AccountDetailView }) {
  const { dateEnd, dateStart, handleQuickFilter, setDateEnd, setDateStart } = ctx
  return (
    <>
      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4 bg-white p-3 rounded-2xl border border-slate-100 shadow-sm">
        <div className="hidden items-center gap-2 text-slate-400 mr-2 sm:flex">
          <Filter className="h-4 w-4" />
          <span className="text-xs font-bold uppercase tracking-wider">Filtres</span>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <Select onValueChange={handleQuickFilter}>
            <SelectTrigger className="h-11 w-full sm:h-9 sm:w-[140px] bg-slate-50 border-slate-200 text-xs font-medium">
              <SelectValue placeholder="Période rapide" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tout l'historique</SelectItem>
              <SelectItem value="current-month">Ce mois-ci</SelectItem>
              <SelectItem value="last-3-months">3 derniers mois</SelectItem>
              <SelectItem value="current-year">Cette année</SelectItem>
            </SelectContent>
          </Select>

          <div className="h-4 w-px bg-slate-200 mx-1 hidden sm:block" />

          <div className="flex items-center gap-2 bg-slate-50 rounded-lg border border-slate-200 px-3 py-0.5 max-sm:h-11">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            <Input 
              type="date" 
              value={dateStart} 
              onChange={(e) => setDateStart(e.target.value)} 
              className="h-8 min-w-0 flex-1 border-none bg-transparent p-0 text-base font-medium shadow-none focus-visible:ring-0 sm:w-[120px] sm:flex-none sm:text-xs" 
            />
            <span className="text-slate-300 text-[10px] font-bold">À</span>
            <Input 
              type="date" 
              value={dateEnd} 
              onChange={(e) => setDateEnd(e.target.value)} 
              className="h-8 min-w-0 flex-1 border-none bg-transparent p-0 text-base font-medium shadow-none focus-visible:ring-0 sm:w-[120px] sm:flex-none sm:text-xs" 
            />
            {(dateStart || dateEnd) && (
              <Button aria-label="Ajouter" 
                variant="ghost" 
                size="icon" 
                onClick={() => { setDateStart(""); setDateEnd(""); }} 
                className="h-8 w-8 shrink-0 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-full sm:h-6 sm:w-6"
              >
                <Plus className="h-4 w-4 rotate-45" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
