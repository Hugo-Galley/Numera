import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { keepSeriesOrder, numberFormatter } from "@/lib/chartTooltip"
import { TrendingUp } from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import type { WealthForecastView } from "./useWealthForecast"

/** Graphique de la projection. */
export function ForecastChartCard({ ctx }: { ctx: WealthForecastView }) {
  const { t } = useTranslation("tools")
  const { boostedShown, data } = ctx
  return (
    <>
      <Card className="shadow-sm border-slate-100">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-blue-500" /> {t("forecastChartCard.evolutionPrevue")}
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[260px] px-2 md:h-[360px] md:px-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.points} margin={{ top: 10, right: 12, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="year" tickFormatter={(v) => t("misc.xYears", { count: Number(v) })} tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd" minTickGap={16} />
              <YAxis
                tick={{ fontSize: 12, fill: "#64748b" }}
                tickFormatter={(v) => `${Math.round(v / 1000)}k€`}
                width={52}
              />
              <Tooltip itemSorter={keepSeriesOrder}
                contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                labelFormatter={(v) => t("misc.inXYears", { count: Number(v) })}
                formatter={numberFormatter((v: number) => formatCurrency(v, "EUR"))}
              />
              <Legend itemSorter={null} />
              <Line type="monotone" dataKey="base" name={t("forecastChartCard.auRythmeActuel")} stroke="#3b82f6" strokeWidth={3} dot={false} />
              {boostedShown && (
                <Line type="monotone" dataKey="boosted" name={t("misc.withExtra", { sign: data.extra_monthly > 0 ? "+" : "", amount: data.extra_monthly })} stroke="#10b981" strokeWidth={3} dot={false} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </>
  )
}
