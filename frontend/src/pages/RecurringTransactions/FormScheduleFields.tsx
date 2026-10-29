import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { CalendarIcon, ChevronDown } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import { format } from "date-fns"
import { fr } from "date-fns/locale"
import { MONTHS } from "./types"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Formulaire : jour et mois exclus, date de début, génération automatique et note. */
export function FormScheduleFields({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { formData, isIrregularSubmenuOpen, setFormData, setIsIrregularSubmenuOpen } = ctx
  return (
    <>
      {formData.frequency === "monthly" && (
        <div className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-3">
          <button
            type="button"
            onClick={() => setIsIrregularSubmenuOpen(!isIrregularSubmenuOpen)}
            className="flex items-center justify-between w-full text-left text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-slate-200/70 text-slate-600">
                <CalendarIcon className="h-3.5 w-3.5" />
              </span>
              <div>
                <span>Mois irréguliers (exclusions)</span>
                {formData.excluded_months.length > 0 ? (
                  <span className="ml-2 text-[10px] font-bold text-amber-600 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-full">
                    {formData.excluded_months.length} exclu{formData.excluded_months.length > 1 ? "s" : ""} (
                    {formData.excluded_months.map(m => MONTHS.find(mon => mon.value === m)?.label).join(", ")})
                  </span>
                ) : (
                  <span className="ml-2 text-[10px] text-slate-400 font-normal">Optionnel</span>
                )}
              </div>
            </div>
            <ChevronDown className={cn("h-4 w-4 text-slate-400 transition-transform duration-200", isIrregularSubmenuOpen && "rotate-180")} />
          </button>

          {isIrregularSubmenuOpen && (
            <div className="pt-2 border-t border-slate-200/60 space-y-2">
              <p className="text-[11px] text-slate-500">
                Sélectionnez les mois où ce montant ne sera <strong className="font-semibold text-slate-700">pas débité</strong> (ex: non prélevé en mai et octobre).
              </p>
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-1.5 pt-1">
                {MONTHS.map((m) => {
                  const isExcluded = formData.excluded_months.includes(m.value)
                  return (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => {
                        setFormData(prev => ({
                          ...prev,
                          excluded_months: isExcluded
                            ? prev.excluded_months.filter(val => val !== m.value)
                            : [...prev.excluded_months, m.value].sort((a, b) => a - b)
                        }))
                      }}
                      className={cn(
                        "py-1.5 px-2 text-xs font-medium rounded-md border text-center transition-all",
                        isExcluded
                          ? "bg-rose-50 border-rose-300 text-rose-700 font-bold shadow-xs line-through"
                          : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                      )}
                      title={isExcluded ? `Mois exclu (${m.label})` : `Mois actif (${m.label})`}
                    >
                      {m.label}
                    </button>
                  )
                })}
              </div>
              {formData.excluded_months.length > 0 && (
                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, excluded_months: [] }))}
                    className="text-[10px] text-slate-400 hover:text-slate-600 underline"
                  >
                    Réinitialiser les exclusions
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="grid gap-2">
        <Label>Date de début</Label>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                "w-full justify-start text-left font-normal",
                !formData.start_date && "text-muted-foreground"
              )}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {formData.start_date 
                ? format(new Date(formData.start_date), "dd MMMM yyyy", { locale: fr })
                : <span>Choisir une date...</span>
              }
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0">
            <Calendar
              mode="single"
              selected={formData.start_date ? new Date(formData.start_date) : undefined}
              onSelect={(d) => d && setFormData({ ...formData, start_date: format(d, "yyyy-MM-dd") })}
            />
          </PopoverContent>
        </Popover>
      </div>

      <div className="flex items-center justify-between p-3 border rounded-md bg-slate-50">
        <div className="space-y-0.5">
          <Label>Génération automatique</Label>
          <p className="text-xs text-slate-500">Créer les transactions sans intervention.</p>
        </div>
        <Checkbox 
          checked={formData.auto_generate}
          onCheckedChange={(checked: any) => setFormData({ ...formData, auto_generate: !!checked })}
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="note">Note</Label>
        <Input
          id="note"
          value={formData.note}
          onChange={(e) => setFormData({ ...formData, note: e.target.value })}
          placeholder="Note facultative..."
        />
      </div>
    </>
  )
}
