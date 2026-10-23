import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { WealthSimulator } from "@/components/analytics/WealthSimulator"
import { WealthForecast } from "@/components/tools/WealthForecast"
import { Button } from "@/components/ui/button"

export default function Tools() {
  const [totalValue, setTotalValue] = useState(0)
  const [loading, setLoading] = useState(true)
  const [advanced, setAdvanced] = useState(false)

  useEffect(() => {
    async function loadData() {
      try {
        const basic = await api.get("/analytics/investments-allocation")
        setTotalValue(basic.total_current_value || 0)
      } catch (error) {
        console.error("Erreur lors du chargement de l'allocation", error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  return (
    <div className="space-y-6 md:space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Outils</h1>
        <p className="text-sm text-muted-foreground md:text-base">Simulez et projetez l'évolution de votre patrimoine.</p>
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
        <WealthForecast />
      )}

      <div className="flex justify-center">
        <Button variant="ghost" size="sm" className="h-11 md:h-9" onClick={() => setAdvanced((v) => !v)}>
          {advanced ? "Retour à la vue simple" : "Mode avancé"}
        </Button>
      </div>
    </div>
  )
}
