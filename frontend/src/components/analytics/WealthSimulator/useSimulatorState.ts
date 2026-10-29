import { api } from "@/lib/api"
import { safeStorage } from "@/lib/storage"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { LifeEvent, AssetClass, defaultAssetClasses } from "./types"

/** Paramètres (mémorisés dans le navigateur), allocation et appel de la simulation. */
export function useSimulatorState(p: { initialCapitalDefault: number }) {
  const { initialCapitalDefault } = p
  // Load initial params from localStorage if available, else fall back to defaults
  const [params, setParams] = useState(() => {
    const saved = safeStorage.getItem("numera_wealth_sim_params")
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        return {
          ...parsed,
          initial_capital: initialCapitalDefault // Reset initial capital default if prop changes
        }
      } catch {}
    }
    return {
      initial_capital: initialCapitalDefault,
      monthly_contribution: 500,
      annual_return_pct: 7,
      years: 20,
      volatility_pct: 0,
      inflation_rate_pct: 2.0,
      contribution_indexation_pct: 0,
      tax_rate_pct: 0,
      tax_deferred: true,
    }
  })

  const [events, setEvents] = useState<LifeEvent[]>(() => {
    const saved = safeStorage.getItem("numera_wealth_sim_events")
    if (saved) {
      try { return JSON.parse(saved) } catch {}
    }
    return []
  })

  const [newEvent, setNewEvent] = useState<LifeEvent>({
    year: 5,
    amount: -10000,
    label: ""
  })

  // Asset Allocation State
  const [useAllocation, setUseAllocation] = useState(() => {
    return safeStorage.getItem("numera_wealth_sim_use_alloc") === "true"
  })

  const [assetClasses, setAssetClasses] = useState<AssetClass[]>(() => {
    const saved = safeStorage.getItem("numera_wealth_sim_asset_classes")
    if (saved) {
      try { return JSON.parse(saved) } catch {}
    }
    return defaultAssetClasses
  })

  const [editingAsset, setEditingAsset] = useState<AssetClass | null>(null)

  // UI state for display
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [showInflationAdjusted, setShowInflationAdjusted] = useState(false)
  const [showMonteCarlo, setShowMonteCarlo] = useState(true)

  // Weighted asset class parameters:
  const totalAlloc = assetClasses.reduce((sum, item) => sum + item.pct, 0)
  const computedReturn = Number(
    (assetClasses.reduce((sum, item) => sum + (item.pct * item.expectedReturn), 0) / 100).toFixed(2)
  )
  const computedVolatility = Number(
    (assetClasses.reduce((sum, item) => sum + (item.pct * item.volatility), 0) / 100).toFixed(2)
  )

  // Sync to local storage
  useEffect(() => {
    safeStorage.setItem("numera_wealth_sim_params", JSON.stringify(params))
  }, [params])

  useEffect(() => {
    safeStorage.setItem("numera_wealth_sim_events", JSON.stringify(events))
  }, [events])

  useEffect(() => {
    safeStorage.setItem("numera_wealth_sim_use_alloc", String(useAllocation))
  }, [useAllocation])

  useEffect(() => {
    safeStorage.setItem("numera_wealth_sim_asset_classes", JSON.stringify(assetClasses))
  }, [assetClasses])

  // Sync initialCapitalDefault if it changes from parent
  useEffect(() => {
    setParams((prev: any) => ({ ...prev, initial_capital: initialCapitalDefault }))
  }, [initialCapitalDefault])

  // Main data fetcher
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        let returnPct = params.annual_return_pct
        let volPct = params.volatility_pct

        if (useAllocation) {
          if (totalAlloc === 100) {
            returnPct = computedReturn
            volPct = computedVolatility
          } else {
            // Wait for allocation to equal 100% to avoid rendering inconsistent data
            setLoading(false)
            return
          }
        }

        const queryParams = new URLSearchParams({
          initial_capital: params.initial_capital.toString(),
          monthly_contribution: params.monthly_contribution.toString(),
          annual_return_pct: returnPct.toString(),
          years: params.years.toString(),
          volatility_pct: volPct.toString(),
          inflation_rate_pct: params.inflation_rate_pct.toString(),
          contribution_indexation_pct: params.contribution_indexation_pct.toString(),
          tax_rate_pct: params.tax_rate_pct.toString(),
          tax_deferred: params.tax_deferred.toString(),
          events: JSON.stringify(events.filter(e => e.year <= params.years))
        })

        const res = await api.get(`/analytics/wealth-simulation?${queryParams.toString()}`)
        setData(res)
      } catch (error) {
        toast.error("Erreur lors de la simulation")
      } finally {
        setLoading(false)
      }
    }

    const timeoutId = setTimeout(fetchData, 400)
    return () => clearTimeout(timeoutId)
  }, [params, events, useAllocation, assetClasses, totalAlloc, computedReturn, computedVolatility])

  return { params, setParams, events, setEvents, newEvent, setNewEvent, useAllocation, setUseAllocation, assetClasses, setAssetClasses, editingAsset, setEditingAsset, data, setData, loading, setLoading, showInflationAdjusted, setShowInflationAdjusted, showMonteCarlo, setShowMonteCarlo, totalAlloc, computedReturn, computedVolatility }
}
