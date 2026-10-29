import { ArrowDownCircle, ArrowUpCircle, Calendar as CalendarIcon, CheckCircle2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { cn, formatCurrency } from "@/lib/utils"
import type { CalendarCtx } from "./useCalendar"

/** Dialogue du détail d'un jour. */
export function DayDetailDialog({ ctx }: { ctx: CalendarCtx }) {
  const { getBalanceForDay, handleValidate, isDayDetailOpen, isPrivacyMode, month, selectedDay, selectedDayEvents, setIsDayDetailOpen, validating, year } = ctx
  return (
    <>
      <Dialog open={isDayDetailOpen} onOpenChange={setIsDayDetailOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5 text-slate-400" />
              {selectedDay && new Date(selectedDay).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </DialogTitle>
            <DialogDescription>
              Flux financiers pour cette journée
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {selectedDayEvents.length > 0 ? (
              <div className="space-y-3">
                {selectedDayEvents.map((ev) => {
                  const isEvNegative = ev.type === "Sortie" || ev.type === "retrait"
                  return (
                    <div key={ev.id} className="flex items-center justify-between gap-3 p-3 md:p-2 rounded-lg border border-slate-100 bg-slate-50/50">
                      <div className="flex items-center gap-3 min-w-0">
                        {ev.ticker || ev.logo ? (
                          <CompanyLogo ticker={ev.ticker} name={ev.name} logo={ev.logo} className="h-8 w-8 rounded-lg shadow-2xs" />
                        ) : isEvNegative ? (
                          <ArrowDownCircle className="h-8 w-8 shrink-0 text-slate-400" />
                        ) : (
                          <ArrowUpCircle className="h-8 w-8 shrink-0 text-emerald-500" />
                        )}
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-slate-900 break-words">{ev.name}</p>
                          <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                            {ev.ticker && (
                              <>
                                <span className="text-[10px] text-slate-400 font-mono font-medium">{ev.ticker}</span>
                                <span className="text-slate-300">•</span>
                              </>
                            )}
                            {ev.is_projected && <Badge variant="secondary" className="h-4 text-[9px] px-1 bg-amber-100 text-amber-700 hover:bg-amber-100 border-none">PRÉVU</Badge>}
                            <span className="text-[10px] text-slate-500 uppercase font-medium tracking-wider">{ev.type}</span>
                            {ev.quantity && (
                              <span className="text-[10px] text-slate-400 font-mono">• {ev.quantity} part(s)</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <p className={cn(
                          "text-sm font-bold whitespace-nowrap tabular-nums",
                          isEvNegative ? "text-slate-900" : "text-emerald-600"
                        )}>
                          {isEvNegative ? "-" : "+"}{isPrivacyMode ? "***" : formatCurrency(ev.amount, ev.currency)}
                        </p>
                        {ev.is_projected && ev.recurring_id && (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="h-9 md:h-6 text-xs md:text-[10px] gap-1 px-2 md:px-1.5 hover:bg-emerald-50 hover:text-emerald-700"
                            onClick={() => handleValidate(ev)}
                            disabled={validating}
                          >
                            <CheckCircle2 className="h-3 w-3" />
                            Valider
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-400 italic">
                Aucune transaction ce jour
              </div>
            )}

            {selectedDay && (
              <div className="pt-4 border-t flex items-center justify-between text-sm">
                <span className="text-slate-500 font-medium">Solde estimé fin de journée</span>
                <span className={cn(
                  "font-bold",
                  (getBalanceForDay(new Date(selectedDay).getDate()) || 0) < 0 ? "text-red-600" : "text-slate-900"
                )}>
                  {isPrivacyMode ? "***" : formatCurrency(getBalanceForDay(new Date(selectedDay).getDate()) || 0, "EUR")}
                </span>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
