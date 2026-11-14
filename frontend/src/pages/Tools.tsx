import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useState, useEffect } from "react"
import { WealthSimulator } from "@/components/analytics/WealthSimulator"
import { WealthForecast } from "@/components/tools/WealthForecast"
import { FireProjection } from "@/components/tools/FireProjection"
import { Button } from "@/components/ui/button"
import { getAnalyticsInvestmentsAllocation } from "@/lib/api/analytics"

export default function Tools() {
  const { t } = useTranslation("tools")
  const [totalValue, setTotalValue] = useState(0)
  const [loading, setLoading] = useState(true)
  const [advanced, setAdvanced] = useState(false)

  useEffect(() => {
    async function loadData() {
      try {
        const basic = await getAnalyticsInvestmentsAllocation()
        setTotalValue(basic.total_current_value || 0)
      } catch (error) {
        console.error("Erreur lors du chargement de l'allocation", error)
        toast.error(t("tools.impossibleDeChargerLAllocation"))
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [t])

  return (
    <div className="space-y-6 md:space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{t("tools.outils")}</h1>
        <p className="text-sm text-muted-foreground md:text-base">{t("tools.simulezEtProjetezLEvolution")}</p>
      </div>

      {advanced ? (
        !loading ? (
          <WealthSimulator initialCapitalDefault={totalValue} />
        ) : (
          <div className="flex items-center justify-center h-[400px]">
            <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
          </div>
        )
      ) : (
        <>
          <WealthForecast />
          <FireProjection />
        </>
      )}

      <div className="flex justify-center">
        <Button variant="ghost" size="sm" className="h-11 md:h-9" onClick={() => setAdvanced((v) => !v)}>
          {advanced ? t("tools.retourALaVueSimple") : t("tools.modeAvance")}
        </Button>
      </div>
    </div>
  )
}
