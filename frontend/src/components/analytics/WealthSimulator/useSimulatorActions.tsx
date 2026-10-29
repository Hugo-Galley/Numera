import { Info } from "lucide-react"
import { formatCurrency as formatCurrencyBase } from "@/lib/utils"
import { toast } from "sonner"
import { AssetClass } from "./types"
import type { useSimulatorState } from "./useSimulatorState"

/** Actions sur les événements de vie et les classes d'actifs, infobulle du graphique. */
export function useSimulatorActions(p: { initialCapitalDefault: number } & ReturnType<typeof useSimulatorState>) {
  const { params, events, setEvents, newEvent, setNewEvent, useAllocation, assetClasses, setAssetClasses, setEditingAsset, showInflationAdjusted, showMonteCarlo, computedVolatility } = p
  const formatCurrency = (value: number) => formatCurrencyBase(value, "EUR", { maximumFractionDigits: 0 })

  const handleAddEvent = () => {
    if (!newEvent.label.trim()) {
      toast.error("Veuillez saisir un libellé pour l'événement.")
      return
    }
    if (newEvent.year < 1 || newEvent.year > params.years) {
      toast.error(`L'année de l'événement doit être comprise entre 1 et ${params.years}.`)
      return
    }
    setEvents(prev => [...prev, newEvent].sort((a, b) => a.year - b.year))
    setNewEvent({ year: Math.min(newEvent.year + 1, params.years), amount: -10000, label: "" })
    toast.success("Événement ajouté à la simulation")
  }

  const handleRemoveEvent = (index: number) => {
    setEvents(prev => prev.filter((_, i) => i !== index))
    toast.success("Événement supprimé")
  }

  const updateAsset = (id: string, updates: Partial<AssetClass>) => {
    setAssetClasses(prev => prev.map(item => {
      if (item.id === id) {
        return { ...item, ...updates }
      }
      return item
    }))
  }

  const handleAddAsset = () => {
    const newId = String(Date.now())
    const newClass = { id: newId, name: "Nouvelle classe d'actifs", pct: 0, expectedReturn: 6, volatility: 10 }
    setAssetClasses(prev => [...prev, newClass])
    setEditingAsset(newClass)
  }

  const handleDeleteAsset = (id: string) => {
    if (assetClasses.length <= 1) {
      toast.error("Vous devez conserver au moins une classe d'actifs.")
      return
    }
    setAssetClasses(prev => prev.filter(item => item.id !== id))
    toast.success("Actif supprimé")
  }

  const handlePresetAllocation = (preset: "balanced_60_40" | "all_actions" | "all_weather" | "crypto_tilted") => {
    if (preset === "balanced_60_40") {
      setAssetClasses([
        { id: "1", name: "Actions / ETF World", pct: 60, expectedReturn: 8, volatility: 15 },
        { id: "2", name: "Obligations d'État", pct: 40, expectedReturn: 3.5, volatility: 5 }
      ])
    } else if (preset === "all_actions") {
      setAssetClasses([
        { id: "1", name: "Actions / ETF", pct: 100, expectedReturn: 8.5, volatility: 16 }
      ])
    } else if (preset === "all_weather") {
      setAssetClasses([
        { id: "1", name: "Actions ETF World", pct: 30, expectedReturn: 8, volatility: 15 },
        { id: "2", name: "Obligations LT", pct: 40, expectedReturn: 4, volatility: 7 },
        { id: "3", name: "Obligations MT", pct: 15, expectedReturn: 3, volatility: 4 },
        { id: "4", name: "Matières Premières / Or", pct: 15, expectedReturn: 5, volatility: 12 }
      ])
    } else if (preset === "crypto_tilted") {
      setAssetClasses([
        { id: "1", name: "ETF Actions World", pct: 70, expectedReturn: 8, volatility: 15 },
        { id: "2", name: "Cryptomonnaies (BTC/ETH)", pct: 10, expectedReturn: 25, volatility: 60 },
        { id: "3", name: "Assurance-Vie / Fonds Euro", pct: 20, expectedReturn: 2.5, volatility: 0 }
      ])
    }
    toast.success("Preset d'allocation appliqué")
  }

  const isVolatile = useAllocation ? computedVolatility > 0 : params.volatility_pct > 0
  const activeEventsCount = events.filter(e => e.year <= params.years).length

  // Custom tooltips for Recharts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload
      const eventStr = point.event_applied
      
      return (
        <div className="bg-white p-3 border rounded-lg shadow-md text-xs space-y-2 max-w-[280px]">
          <p className="font-bold border-b pb-1">Année {label}</p>
          
          {isVolatile && showMonteCarlo ? (
            <div className="space-y-1">
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Optimiste (P90):</span>
                <span className="font-semibold text-emerald-600 amount-blur">
                  {formatCurrency(showInflationAdjusted ? point.total_value_p90_real : point.total_value_p90)}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Médian (P50):</span>
                <span className="font-bold text-indigo-600 amount-blur">
                  {formatCurrency(showInflationAdjusted ? point.total_value_p50_real : point.total_value_p50)}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Pessimiste (P10):</span>
                <span className="font-semibold text-rose-600 amount-blur">
                  {formatCurrency(showInflationAdjusted ? point.total_value_p10_real : point.total_value_p10)}
                </span>
              </div>
              <div className="border-t pt-1 mt-1 flex justify-between gap-4 text-[10px] text-slate-400">
                <span>Versements cum.:</span>
                <span className="amount-blur">{formatCurrency(point.total_contributions)}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Capital Initial:</span>
                <span className="font-medium amount-blur">{formatCurrency(point.initial_capital)}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Versements:</span>
                <span className="font-medium amount-blur">{formatCurrency(point.total_contributions)}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Intérêts (Nets):</span>
                <span className="font-medium text-emerald-600 amount-blur">{formatCurrency(point.total_interest)}</span>
              </div>
              {point.total_tax_paid > 0 && (
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500">Impôts dues:</span>
                  <span className="font-medium text-rose-600 amount-blur">-{formatCurrency(point.total_tax_paid)}</span>
                </div>
              )}
              <div className="pt-1 mt-1 border-t flex justify-between gap-4">
                <span className="font-bold">Total (Nominal):</span>
                <span className="font-bold amount-blur">{formatCurrency(point.total_value)}</span>
              </div>
              {showInflationAdjusted && (
                <div className="flex justify-between gap-4 text-slate-500">
                  <span>Total (Réel/Ajusté):</span>
                  <span className="font-bold amount-blur">{formatCurrency(point.total_value_real)}</span>
                </div>
              )}
            </div>
          )}
          
          {eventStr && (
            <div className="mt-1.5 pt-1.5 border-t border-dashed border-slate-200 text-amber-600 font-medium text-[10px] flex items-start gap-1">
              <Info className="h-3 w-3 mt-0.5 shrink-0" />
              <span>Événement : {eventStr}</span>
            </div>
          )}
        </div>
      )
    }
    return null
  }

  return { formatCurrency, handleAddEvent, handleRemoveEvent, updateAsset, handleAddAsset, handleDeleteAsset, handlePresetAllocation, isVolatile, activeEventsCount, CustomTooltip }
}
