import { Badge } from "@/components/ui/badge"
import { Calendar, Clock, Coins, Percent } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { TabsContent } from "@/components/ui/tabs"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Onglet général : capital, versements, rendement et durée. */
export function BaseTab({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { computedReturn, params, setParams, useAllocation } = ctx
  return (
    <>
      {/* CONTENU ONGLET 1: GENERAL */}
      <TabsContent value="base" className="space-y-4 m-0 outline-none">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="initial_capital" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <Coins className="h-3.5 w-3.5 text-slate-400" />
              Capital Initial
            </Label>
            <Input
              id="initial_capital"
              type="number" inputMode="decimal"
              value={params.initial_capital}
              onChange={(e) => setParams({ ...params, initial_capital: Number(e.target.value) })}
              className="h-11 md:h-9 text-base md:text-sm bg-white"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="monthly_contribution" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              Versement Mensuel
            </Label>
            <Input
              id="monthly_contribution"
              type="number" inputMode="decimal"
              value={params.monthly_contribution}
              onChange={(e) => setParams({ ...params, monthly_contribution: Number(e.target.value) })}
              className="h-11 md:h-9 text-base md:text-sm bg-white"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="years" className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              Durée (années)
            </Label>
            <Input
              id="years"
              type="number" inputMode="decimal"
              min={1}
              max={50}
              value={params.years}
              onChange={(e) => setParams({ ...params, years: Number(e.target.value) })}
              className="h-11 md:h-9 text-base md:text-sm bg-white"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="annual_return_pct" className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span className="flex items-center gap-1.5">
                <Percent className="h-3.5 w-3.5 text-slate-400" />
                Rendement Annuel (%)
              </span>
              {useAllocation && (
                <Badge variant="outline" className="text-[9px] text-emerald-600 bg-emerald-50/50 border-emerald-200">Calculé</Badge>
              )}
            </Label>
            <Input
              id="annual_return_pct"
              type="number" inputMode="decimal"
              step="0.1"
              disabled={useAllocation}
              value={useAllocation ? computedReturn : params.annual_return_pct}
              onChange={(e) => setParams({ ...params, annual_return_pct: Number(e.target.value) })}
              className="h-11 md:h-9 text-base md:text-sm bg-white"
            />
          </div>
        </div>
      </TabsContent>

    </>
  )
}
