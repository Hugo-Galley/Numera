import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Landmark } from "lucide-react"
import { Link } from "react-router-dom"
import { Skeleton } from "@/components/ui/skeleton"
import { KIND_LABELS } from "./types"
import { WrapperCardView } from "./TaxWidgets"
import type { TaxCtx } from "./useTax"

/** Plafonds et dates clés des enveloppes. */
export function WrappersSection({ ctx }: { ctx: TaxCtx }) {
  const { t } = useTranslation("tax")
  const { applySuggestion, cards, loadingOverview, suggestions } = ctx
  return (
    <>
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">{t("wrappersSection.plafondsEtDatesCles")}</h2>
        {suggestions.length > 0 && (
          <Card className="border-amber-200 bg-amber-50/50">
            <CardContent className="space-y-3 p-4">
              <p className="text-sm text-slate-700">
                {t("wrappersSection.cesComptesNOntPas")}
              </p>
              {suggestions.map((s) => (
                <div key={s.account_id} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span className="text-sm">
                    <span className="font-semibold">{s.account_name}</span>{i18n.t("misc.probable", { ns: "tax", kind: KIND_LABELS[s.kind] })}
                  </span>
                  <Button size="sm" variant="outline" className="h-10 sm:h-9" onClick={() => applySuggestion(s)}>
                    {i18n.t("misc.trackAs", { ns: "tax", kind: KIND_LABELS[s.kind] })}
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
        {loadingOverview ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-44" />
            <Skeleton className="h-44" />
          </div>
        ) : cards.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
              <Landmark className="h-8 w-8 text-slate-400" />
              <p className="text-sm text-slate-600">
                {t("wrappersSection.aucunCompteNAD")}
              </p>
              <Button asChild variant="outline" className="h-11 w-full sm:h-10 sm:w-auto"><Link to="/accounts">{t("wrappersSection.allerAuxComptes")}</Link></Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {cards.map((card) => <WrapperCardView key={card.account_id} card={card} />)}
          </div>
        )}
      </section>
    </>
  )
}
