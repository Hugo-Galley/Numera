import { Forecast } from "./types"

import { useForecastData } from "./useForecastData"

/** Assemble l'état, les chargements et les actions de WealthForecast. */
export function useWealthForecast() {
  const forecastData = useForecastData()
  return { ...forecastData }
}

export type WealthForecastCtx = ReturnType<typeof useWealthForecast>
/** Contexte passé aux sections, une fois les données chargées (non nulles). */
export type WealthForecastView = WealthForecastCtx & { data: Forecast; boostedShown: boolean; final: number }
