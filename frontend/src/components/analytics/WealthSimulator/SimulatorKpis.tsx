import { Badge } from "@/components/ui/badge"
import { Calendar, Plus, TrendingDown, TrendingUp } from "lucide-react"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Indicateurs finaux et distribution Monte-Carlo. */
export function SimulatorKpis({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { data, formatCurrency, isVolatile, params, showInflationAdjusted } = ctx
  return (
    <>
      {/* BLOC DES METRICS KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* KPI 1 : PATRIMOINE TOTAL FINAL */}
        <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 flex flex-col justify-between shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Patrimoine Final</span>
            <Badge variant="secondary" className="bg-indigo-50 text-indigo-700 text-[9px] hover:bg-indigo-50 border-none font-bold">Médian</Badge>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-black text-indigo-650 amount-blur">
              {formatCurrency(data?.total_final || 0)}
            </span>
            <span className="text-[9px] text-slate-400 mt-1 leading-normal">
              {params.inflation_rate_pct > 0 && data?.total_final_real ? (
                <>Soit <span className="amount-blur font-semibold text-slate-655">{formatCurrency(data.total_final_real)}</span> en pouvoir d'achat</>
              ) : (
                "Pouvoir d'achat nominal"
              )}
            </span>
          </div>
        </div>

        {/* KPI 2 : TOTAL VERSEMENTS (EPARGNE CUMULEE) */}
        <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 flex flex-col justify-between shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Cumul Épargné</span>
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-black text-slate-700 amount-blur">
              {formatCurrency((params.initial_capital || 0) + (data?.total_contributions || 0))}
            </span>
            <span className="text-[9px] text-slate-400 mt-1 leading-normal">
              Dont <span className="amount-blur font-semibold text-slate-655">{formatCurrency(params.initial_capital)}</span> de départ
            </span>
          </div>
        </div>

        {/* KPI 3 : PLUS-VALUES ET GAINS GENERES */}
        <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 flex flex-col justify-between shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Plus-values Nettes</span>
            <span className="text-[9px] text-emerald-700 font-bold bg-emerald-50 px-1 rounded border border-emerald-100">Gains</span>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-black text-emerald-600 amount-blur">
              +{formatCurrency(data?.total_interest || 0)}
            </span>
            <span className="text-[9px] text-slate-400 mt-1 leading-normal">
              {params.tax_rate_pct > 0 && data?.total_tax_paid ? (
                <>Taxes estimées : <span className="amount-blur font-semibold text-rose-500">-{formatCurrency(data.total_tax_paid)}</span></>
              ) : (
                "Exonéré d'impôt"
              )}
            </span>
          </div>
        </div>
      </div>

      {/* BANNIÈRE DE DISTRIBUTION DES SCÉNARIOS MONTE CARLO */}
      {isVolatile && data && (
        <div className="grid grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-100 shadow-sm">
          <div className="flex flex-col">
            <span className="text-[9px] text-rose-550 uppercase font-bold tracking-wider flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              Scénario Catastrophe (P10)
            </span>
            <span className="text-base font-black text-rose-600 amount-blur mt-1">
              {formatCurrency(showInflationAdjusted ? data.items[data.items.length - 1].total_value_p10_real : data.pessimistic_final)}
            </span>
            <span className="text-[9px] text-slate-455 mt-0.5">90% de chances de dépasser ce montant</span>
          </div>
          <div className="flex flex-col border-l border-slate-200 pl-4">
            <span className="text-[9px] text-emerald-600 uppercase font-bold tracking-wider flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              Scénario Idéal (P90)
            </span>
            <span className="text-base font-black text-emerald-600 amount-blur mt-1">
              {formatCurrency(showInflationAdjusted ? data.items[data.items.length - 1].total_value_p90_real : data.optimistic_final)}
            </span>
            <span className="text-[9px] text-slate-455 mt-0.5">10% de chances de dépasser ce montant</span>
          </div>
        </div>
      )}
    </>
  )
}
