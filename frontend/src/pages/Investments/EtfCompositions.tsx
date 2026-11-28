import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { appLocale } from "@/i18n/locale"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowRight, Layers, RefreshCw } from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import { CompositionOrigin } from "./CompositionOrigin"
import { COMPOSITION_FIELDS, SOURCE_LABELS } from "./types"
import type { InvestmentsCtx } from "./useInvestments"

/** Origine des compositions des ETF détenus (sources, fraîcheur, fiche de chaque fonds). */
export function EtfCompositions({ ctx }: { ctx: InvestmentsCtx }) {
  const { t } = useTranslation("investments")
  const { diversity, refreshCompositions, refreshingCompositions } = ctx
  return (
    <>
      {diversity && diversity.etf_compositions.length > 0 && (
        <Card className="shadow-xs">
          <CardHeader className="border-b pb-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 shrink-0 text-slate-500" />
                <div>
                  <CardTitle className="text-base">{t("etfCompositions.origineDesCompositions")}</CardTitle>
                  <CardDescription className="text-xs">
                    {t("etfCompositions.description")}
                  </CardDescription>
                </div>
              </div>
              <Button variant="outline" size="sm" className="h-10 min-w-10 shrink-0 gap-1.5 md:h-9" aria-label={t("etfCompositions.actualiser")} onClick={refreshCompositions} disabled={refreshingCompositions}>
                <RefreshCw className={`h-3.5 w-3.5 ${refreshingCompositions ? "animate-spin" : ""}`} />
                <span className="hidden sm:inline">{t("etfCompositions.actualiser")}</span>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {diversity.etf_compositions.map((c) => (
                <div key={c.profile_id} className="flex flex-col gap-2 px-4 py-3 md:px-5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{c.profile_name}</div>
                    <div className="text-xs text-muted-foreground wrap-break-word">
                      {c.tickers.join(", ")} · <span className="amount-blur">{formatCurrency(c.value_eur)}</span>
                      {/* Sans composition datée d'un émetteur : au moins la date de la dernière lecture */}
                      {!(c.provider && c.composition_as_of) && (
                        <>
                          {" · "}
                          {c.refreshed_at
                            ? i18n.t("misc.refreshedOn", { ns: "investments", date: new Date(c.refreshed_at + "Z").toLocaleDateString(appLocale()) })
                            : i18n.t("misc.neverRefreshed", { ns: "investments" })}
                        </>
                      )}
                    </div>
                    <CompositionOrigin composition={c} />
                    <Link
                      to={`/investments/etf/${c.profile_id}`}
                      aria-label={t("etfCompositions.voirLaFicheDe", { name: c.profile_name })}
                      className="mt-1 inline-flex min-h-10 items-center gap-1 text-sm font-semibold text-slate-900 underline decoration-slate-300 underline-offset-4 hover:decoration-slate-900"
                    >
                      {t("etfCompositions.voirLaFiche")}
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {COMPOSITION_FIELDS.map(({ key }) => {
                      const label = i18n.t(`misc.fields.${key}`, { ns: "investments" })
                      const source = c.sources[key]
                      return (
                        <Badge
                          key={key}
                          variant="outline"
                          className={`text-[10px] font-medium shadow-none ${source ? SOURCE_LABELS[source].className : "text-slate-400 border-dashed"}`}
                        >
                          {label} : {source ? i18n.t(`misc.sources.${source}`, { ns: "investments" }) : "—"}
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
