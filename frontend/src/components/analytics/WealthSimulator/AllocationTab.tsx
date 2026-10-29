import { Pencil, Plus, Trash2 } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { TabsContent } from "@/components/ui/tabs"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Onglet allocation d'actifs. */
export function AllocationTab({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { assetClasses, handleAddAsset, handleDeleteAsset, handlePresetAllocation, setEditingAsset, setUseAllocation, totalAlloc, updateAsset, useAllocation } = ctx
  return (
    <>
      {/* CONTENU ONGLET 2: ALLOCATION D'ACTIFS */}
      <TabsContent value="allocation" className="space-y-4 m-0 outline-none">
        <div className="flex items-center justify-between bg-white p-2.5 rounded-lg border border-slate-100 shadow-sm">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-bold text-slate-800">Simuler selon une allocation d'actifs</span>
            <span className="text-[10px] text-slate-400">Rendement et risque calculés selon les pondérations</span>
          </div>
          <Switch 
            checked={useAllocation}
            onCheckedChange={setUseAllocation}
          />
        </div>

        {useAllocation ? (
          <div className="space-y-4 pt-1">

            {/* PRESETS D'ALLOCATION */}
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Presets d'allocations</span>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-1.5">
                <button type="button" onClick={() => handlePresetAllocation("balanced_60_40")} className="text-[11px] md:text-[10px] font-semibold py-2.5 md:py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">60/40 Portefeuille</button>
                <button type="button" onClick={() => handlePresetAllocation("all_actions")} className="text-[11px] md:text-[10px] font-semibold py-2.5 md:py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">100% Actions</button>
                <button type="button" onClick={() => handlePresetAllocation("all_weather")} className="text-[11px] md:text-[10px] font-semibold py-2.5 md:py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">All-Weather</button>
                <button type="button" onClick={() => handlePresetAllocation("crypto_tilted")} className="text-[11px] md:text-[10px] font-semibold py-2.5 md:py-1 px-1.5 border rounded bg-white hover:bg-slate-50 transition-colors text-slate-700 text-center truncate">Crypto Tilted</button>
              </div>
            </div>

            {/* LISTE PROPRE DES SLIDERS AVEC CRAYON D'EDITION */}
            <div className="space-y-3.5 max-h-[290px] overflow-y-auto pr-1">
              {assetClasses.map(item => (
                <div key={item.id} className="space-y-1.5 bg-white p-3 rounded-lg border border-slate-100 shadow-sm relative group hover:border-slate-300 transition-all">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-slate-755">{item.name} ({item.pct}%)</span>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-slate-400 mr-1">Rdt: {item.expectedReturn}% | Vol: {item.volatility}%</span>
                      <button
                        type="button"
                        onClick={() => setEditingAsset(item)}
                        className="p-2.5 md:p-1 -m-1.5 md:m-0 hover:bg-slate-100 rounded text-slate-500 hover:text-slate-800 transition-colors"
                        title="Modifier les hypothèses de cet actif"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteAsset(item.id)}
                        className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-rose-600 transition-colors"
                        title="Supprimer cet actif"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>

                  {/* Simple weight slider */}
                  <div className="pt-1">
                    <input 
                      type="range" min="0" max="100" step="1" value={item.pct}
                      onChange={(e) => updateAsset(item.id, { pct: Number(e.target.value) })}
                      className="w-full accent-indigo-650 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* AJOUT CLASSE D'ACTIF */}
            <button
              type="button"
              onClick={handleAddAsset}
              className="w-full border border-dashed border-indigo-200 hover:border-indigo-400 text-indigo-650 hover:bg-indigo-50/50 rounded-lg py-2 text-xs font-bold transition-all flex items-center justify-center gap-1"
            >
              <Plus className="h-4 w-4" />
              Ajouter une classe d'actifs
            </button>

            {/* STATUT PONDERATION */}
            <div className="flex items-center justify-between text-xs px-1 border-t border-slate-100 pt-3">
              <span className="font-semibold text-slate-600">Pondération totale :</span>
              <span className={`font-bold ${totalAlloc === 100 ? "text-emerald-600" : "text-rose-600"}`}>
                {totalAlloc}% {totalAlloc === 100 ? "✓" : "(doit être de 100%)"}
              </span>
            </div>
          </div>
        ) : (
          <div className="text-center py-6 text-xs text-slate-400 bg-white border border-dashed rounded-lg">
            Activez le commutateur ci-dessus pour utiliser une allocation d'actifs personnalisable.
          </div>
        )}
      </TabsContent>

    </>
  )
}
