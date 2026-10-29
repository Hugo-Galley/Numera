import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Trash2 } from "lucide-react"
import { TabsContent } from "@/components/ui/tabs"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Onglet événements de vie. */
export function EventsTab({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { activeEventsCount, events, formatCurrency, handleAddEvent, handleRemoveEvent, newEvent, params, setNewEvent } = ctx
  return (
    <>
      {/* CONTENU ONGLET 4: EVENEMENTS DE VIE */}
      <TabsContent value="events" className="space-y-4 m-0 outline-none">
        <div className="bg-white p-3 rounded-lg border border-slate-150 shadow-inner space-y-3">
          <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
            <Plus className="h-3.5 w-3.5 text-indigo-600" />
            Ajouter un événement (achat, héritage...)
          </span>

          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2 space-y-1">
              <Label className="text-[10px]">Libellé</Label>
              <Input
                placeholder="Achat voiture, Achat RP..."
                value={newEvent.label}
                onChange={(e) => setNewEvent({ ...newEvent, label: e.target.value })}
                className="h-10 md:h-8 text-base md:text-xs bg-slate-50/50"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[10px]">Année</Label>
              <Input
                type="number" inputMode="decimal"
                min={1}
                max={params.years}
                value={newEvent.year}
                onChange={(e) => setNewEvent({ ...newEvent, year: Math.min(Number(e.target.value), params.years) })}
                className="h-10 md:h-8 text-base md:text-xs bg-slate-50/50"
              />
            </div>
          </div>

          <div className="flex gap-2 items-end justify-between">
            <div className="space-y-1 flex-1">
              <Label className="text-[10px]">Montant (€) (négatif = dépense)</Label>
              <Input
                type="number" inputMode="decimal"
                placeholder="Ex: -25000"
                value={newEvent.amount}
                onChange={(e) => setNewEvent({ ...newEvent, amount: Number(e.target.value) })}
                className="h-10 md:h-8 text-base md:text-xs bg-slate-50/50"
              />
            </div>
            <button
              type="button"
              onClick={handleAddEvent}
              className="bg-indigo-600 text-white rounded px-3 py-1.5 text-xs font-semibold hover:bg-indigo-700 h-10 md:h-8 flex items-center gap-1 shrink-0"
            >
              Ajouter
            </button>
          </div>
        </div>

        <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
          <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Événements ajoutés ({activeEventsCount})</h4>

          {activeEventsCount === 0 ? (
            <div className="text-center py-4 border border-dashed rounded text-[11px] text-slate-400 bg-white">
              Aucun événement ponctuel configuré.
            </div>
          ) : (
            events
              .filter(e => e.year <= params.years)
              .map((ev, index) => (
                <div key={index} className="flex justify-between items-center p-2 border bg-white rounded-md text-xs hover:border-slate-300 group">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold text-slate-700">{ev.label}</span>
                    <span className="text-[10px] text-slate-455">Année {ev.year}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`font-bold ${ev.amount >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {ev.amount >= 0 ? "+" : ""}{formatCurrency(ev.amount)}
                    </span>
                    <button aria-label="Supprimer"
                      type="button"
                      onClick={() => handleRemoveEvent(index)}
                      className="text-slate-400 hover:text-rose-650 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))
          )}
        </div>
      </TabsContent>

    </>
  )
}
