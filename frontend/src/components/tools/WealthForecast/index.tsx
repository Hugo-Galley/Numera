import { Skeleton } from "@/components/ui/skeleton"
import { useWealthForecast } from "./useWealthForecast"
import { ForecastSummaryCard } from "./ForecastSummaryCard"
import { ForecastChartCard } from "./ForecastChartCard"
import { ForecastMethodCard } from "./ForecastMethodCard"

export function WealthForecast() {
  const ctx = useWealthForecast()
  const { data, error, loading } = ctx
  if (loading && !data) return <Skeleton className="h-[480px] w-full rounded-xl" />
  if (error || !data) {
    return <p className="text-sm text-rose-600">Impossible de calculer la prévision.</p>
  }

  const boostedShown = data.extra_monthly !== 0
  const final = boostedShown ? data.final_boosted : data.final_base

  const view = { ...ctx, data, boostedShown, final }

  return (
    <div className="space-y-6">
      <ForecastSummaryCard ctx={view} />

      <ForecastChartCard ctx={view} />

      <ForecastMethodCard ctx={view} />
    </div>
  )
}
