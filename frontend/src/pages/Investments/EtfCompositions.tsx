import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Globe, Layers, RefreshCw } from "lucide-react"
import WorldMap from "@/components/ui/WorldMap"
import { formatCurrency } from "@/lib/utils"
import { COMPOSITION_FIELDS, SOURCE_LABELS } from "./types"
import type { InvestmentsCtx } from "./useInvestments"

/** Compositions des ETF et sources. */
export function EtfCompositions({ ctx }: { ctx: InvestmentsCtx }) {
  const { advancedAllocation, diversity, refreshCompositions, refreshingCompositions } = ctx
  return (
    <>
      <Card className="shadow-sm overflow-hidden">
        <CardHeader className="border-b bg-slate-50/50 pb-3">
          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 shrink-0 text-slate-500" />
              <CardTitle className="text-base">Répartition géographique mondiale</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              {diversity && diversity.countries.length > 0 && (
                <Badge variant="secondary" className="bg-slate-100 text-slate-600 text-[10px] pointer-events-none shadow-none border-none">Look-Through</Badge>
              )}
              <Badge variant="outline" className="bg-white">Interactif</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="h-[300px] p-0 relative bg-slate-50/30 md:h-[450px]">
          <div className="absolute top-3 left-3 z-10 rounded-md border bg-white/90 px-2.5 py-1 text-[11px] text-slate-500 shadow-sm backdrop-blur md:top-4 md:left-4 md:px-3 md:py-1.5 md:text-xs">
            <span className="md:hidden">Pincez pour zoomer • Glissez pour déplacer</span><span className="hidden md:inline">Utilisez la molette pour zoomer • Cliquez-glissez pour déplacer</span>
          </div>
          <WorldMap data={
            diversity && diversity.countries.length > 0
              ? diversity.countries.map(c => ({ name: c.name, value: c.value_eur, percentage: c.percentage_stocks }))
              : (advancedAllocation?.by_geographic_zone || [])
          } />
        </CardContent>
      </Card>

      {diversity && diversity.etf_compositions.length > 0 && (
        <Card className="shadow-sm">
          <CardHeader className="border-b pb-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 shrink-0 text-slate-500" />
                <div>
                  <CardTitle className="text-base">Origine des compositions</CardTitle>
                  <CardDescription className="text-xs">
                    Yahoo fournit secteurs et top 10 (pas les pays) ; à défaut, le préréglage intégré est utilisé. La part non couverte apparaît en « Non renseigné ».
                  </CardDescription>
                </div>
              </div>
              <Button variant="outline" size="sm" className="h-10 min-w-10 shrink-0 gap-1.5 md:h-9" aria-label="Actualiser" onClick={refreshCompositions} disabled={refreshingCompositions}>
                <RefreshCw className={`h-3.5 w-3.5 ${refreshingCompositions ? "animate-spin" : ""}`} />
                <span className="hidden sm:inline">Actualiser</span>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {diversity.etf_compositions.map((c) => (
                <div key={c.profile_id} className="flex flex-col gap-2 px-4 py-3 md:px-5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{c.profile_name}</div>
                    <div className="text-xs text-muted-foreground break-words">
                      {c.tickers.join(", ")} · <span className="amount-blur">{formatCurrency(c.value_eur)}</span>
                      {" · "}
                      {c.refreshed_at
                        ? `actualisé le ${new Date(c.refreshed_at + "Z").toLocaleDateString("fr-FR")}`
                        : "jamais actualisé"}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {COMPOSITION_FIELDS.map(({ key, label }) => {
                      const source = c.sources[key]
                      return (
                        <Badge
                          key={key}
                          variant="outline"
                          className={`text-[10px] font-medium shadow-none ${source ? SOURCE_LABELS[source].className : "text-slate-400 border-dashed"}`}
                        >
                          {label} : {source ? SOURCE_LABELS[source].label : "—"}
                        </Badge>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  )
}
