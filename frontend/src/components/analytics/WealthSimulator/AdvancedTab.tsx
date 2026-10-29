import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Scale, Sparkles, TrendingDown } from "lucide-react"
import { TabsContent } from "@/components/ui/tabs"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Onglet risque et fiscalité. */
export function AdvancedTab({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { computedVolatility, params, setParams, useAllocation } = ctx
  return (
    <>
      {/* CONTENU ONGLET 3: RISQUE ET FISCALITE */}
      <TabsContent value="advanced" className="space-y-4 m-0 outline-none">
        <div className="space-y-2">
          <Label htmlFor="volatility_pct" className="flex items-center justify-between text-xs font-semibold text-slate-700">
            <span className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-slate-400" />
              Volatilité Annuelle (%)
            </span>
            {useAllocation && (
              <Badge variant="outline" className="text-[9px] text-emerald-600 bg-emerald-50/50 border-emerald-200">Calculé</Badge>
            )}
          </Label>
          <Input
            id="volatility_pct"
            type="number" inputMode="decimal"
            step="0.5"
            disabled={useAllocation}
            value={useAllocation ? computedVolatility : params.volatility_pct}
            onChange={(e) => setParams({ ...params, volatility_pct: Number(e.target.value) })}
            className="h-11 md:h-9 text-base md:text-sm bg-white"
          />
          <p className="text-[10px] text-slate-400 leading-normal">
            Une volatilité supérieure à 0% déclenche une simulation de Monte Carlo avec 1000 tirages mensuels aléatoires.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="inflation_rate_pct" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <TrendingDown className="h-3.5 w-3.5 text-slate-400" />
              Inflation Annuelle (%)
            </Label>
            <Input
              id="inflation_rate_pct"
              type="number" inputMode="decimal"
              step="0.1"
              value={params.inflation_rate_pct}
              onChange={(e) => setParams({ ...params, inflation_rate_pct: Number(e.target.value) })}
              className="h-11 md:h-9 text-base md:text-sm bg-white"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contribution_indexation_pct" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <Plus className="h-3.5 w-3.5 text-slate-400" />
              Indexation Versements (%)
            </Label>
            <Input
              id="contribution_indexation_pct"
              type="number" inputMode="decimal"
              step="0.5"
              value={params.contribution_indexation_pct}
              onChange={(e) => setParams({ ...params, contribution_indexation_pct: Number(e.target.value) })}
              className="h-11 md:h-9 text-base md:text-sm bg-white"
            />
          </div>
        </div>

        <div className="border-t border-slate-200 pt-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tax_rate_pct" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <Scale className="h-3.5 w-3.5 text-slate-400" />
                Taux d'Impôt (%)
              </Label>
              <Input
                id="tax_rate_pct"
                type="number" inputMode="decimal"
                step="1"
                value={params.tax_rate_pct}
                onChange={(e) => setParams({ ...params, tax_rate_pct: Number(e.target.value) })}
                className="h-11 md:h-9 text-base md:text-sm bg-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tax_deferred" className="text-xs font-semibold text-slate-700">
                Régime Fiscal
              </Label>
              <select
                id="tax_deferred"
                value={params.tax_deferred ? "true" : "false"}
                onChange={(e) => setParams({ ...params, tax_deferred: e.target.value === "true" })}
                className="flex h-11 md:h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-base md:text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950"
              >
                <option value="true">Capitalisation (PEA / Assur-vie)</option>
                <option value="false">Prélèvement Annuel (Compte-titres)</option>
              </select>
            </div>
          </div>
        </div>
      </TabsContent>

    </>
  )
}
