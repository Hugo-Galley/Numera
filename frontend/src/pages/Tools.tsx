import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { WealthSimulator } from "@/components/analytics/WealthSimulator"

export default function Tools() {
  const [totalValue, setTotalValue] = useState(0)
  const [loading, setLoading] = useState(true)

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
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Outils</h1>
        <p className="text-muted-foreground">Simulez et projetez l'évolution de votre patrimoine.</p>
      </div>

      {!loading ? (
        <WealthSimulator initialCapitalDefault={totalValue} />
      ) : (
        <div className="flex items-center justify-center h-[400px]">
          <div className="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        </div>
      )}
    </div>
  )
}
