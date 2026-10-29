import { Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Info, LineChart as LucideLineChart } from "lucide-react"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Graphique de projection, filtres d'affichage et notes. */
export function SimulatorChart({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { CustomTooltip, data, isVolatile, params, setShowInflationAdjusted, setShowMonteCarlo, showInflationAdjusted, showMonteCarlo } = ctx
  return (
    <>
      {/* EN-TETE ET FILTRES D'AFFICHAGE DU GRAPHIQUE */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-3">
        <h3 className="text-xs font-bold text-slate-700 flex items-center gap-1">
          <LucideLineChart className="h-3.5 w-3.5 text-slate-500" />
          Courbe de projection patrimoniale
        </h3>

        <div className="flex items-center gap-4">
          {params.inflation_rate_pct !== 0 && (
            <div className="flex items-center gap-1.5">
              <Switch
                id="toggle-inflation"
                checked={showInflationAdjusted}
                onCheckedChange={setShowInflationAdjusted}
                className="scale-75"
              />
              <Label htmlFor="toggle-inflation" className="text-[11px] font-semibold cursor-pointer text-slate-600">
                Ajuster inflation
              </Label>
            </div>
          )}

          {isVolatile && (
            <div className="flex items-center gap-1.5">
              <Switch
                id="toggle-montecarlo"
                checked={showMonteCarlo}
                onCheckedChange={setShowMonteCarlo}
                className="scale-75"
              />
              <Label htmlFor="toggle-montecarlo" className="text-[11px] font-semibold cursor-pointer text-slate-600">
                Montrer scénarios
              </Label>
            </div>
          )}
        </div>
      </div>

      {/* GRAPHIQUE RECHARTS PRINCIPAL */}
      <div className="h-[260px] md:h-[360px] w-full bg-white rounded-xl border border-slate-50 p-2 shadow-inner">
        <ResponsiveContainer width="100%" height="100%">
          {isVolatile && showMonteCarlo ? (
            <LineChart data={data?.items || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f8fafc" />
              <XAxis 
                dataKey="year" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 10, fill: "#94a3b8" }}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                tickFormatter={(val) => `${(val / 1000).toFixed(0)}k€`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: 10 }} />
              <Line
                type="monotone"
                dataKey={showInflationAdjusted ? "total_value_p90_real" : "total_value_p90"}
                name="Optimiste (P90)"
                stroke="#10b981"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey={showInflationAdjusted ? "total_value_p50_real" : "total_value_p50"}
                name="Médian (P50)"
                stroke="#6366f1"
                strokeWidth={2.5}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey={showInflationAdjusted ? "total_value_p10_real" : "total_value_p10"}
                name="Pessimiste (P10)"
                stroke="#f43f5e"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          ) : (
            <AreaChart data={data?.items || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorInterest" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorContributions" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f8fafc" />
              <XAxis 
                dataKey="year" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 10, fill: "#94a3b8" }}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                tickFormatter={(val) => `${(val / 1000).toFixed(0)}k€`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: 10 }} />
              <Area
                type="monotone"
                dataKey="initial_capital"
                name="Capital Initial"
                stackId="1"
                stroke="#94a3b8"
                fill="#f1f5f9"
                fillOpacity={0.8}
              />
              <Area
                type="monotone"
                dataKey="total_contributions"
                name="Versements"
                stackId="1"
                stroke="#3b82f6"
                fill="url(#colorContributions)"
              />
              <Area
                type="monotone"
                dataKey="total_interest"
                name="Intérêts"
                stackId="1"
                stroke="#10b981"
                fill="url(#colorInterest)"
              />
              {showInflationAdjusted && (
                <Line
                  type="monotone"
                  dataKey="total_value_real"
                  name="Total Réel (Inflation)"
                  stroke="#ef4444"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              )}
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* PETIT DECHARGE LEGAL / NOTES TECHNIQUE */}
      <div className="flex items-start gap-2 text-[10px] text-slate-400 bg-slate-50/50 p-2.5 rounded-lg border border-slate-100 border-dashed">
        <Info className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
        <p className="leading-relaxed">
          Calculs financiers sous-jacents basés sur une composition mensuelle. Les prévisions de Monte Carlo utilisent des écarts-types normaux basés sur les classes d'actifs ou entrées manuelles. 
          Ces courbes sont informatives et ne présagent pas de la performance future de vos capitaux réels.
        </p>
      </div>
    </>
  )
}
