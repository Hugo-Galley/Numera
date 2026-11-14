import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Clock, Info, Plus } from "lucide-react"
import { Link } from "react-router-dom"
import { cn, formatCurrency } from "@/lib/utils"
import type { CalendarCtx } from "./useCalendar"

/** Cartes de synthèse sous la grille. */
export function CalendarSummary({ ctx }: { ctx: CalendarCtx }) {
  const { t } = useTranslation("recurring")
  const { data, embedded, isPrivacyMode } = ctx
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">{t("calendarSummary.prochainesEcheances")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data?.events.filter(e => e.is_projected || e.is_upcoming).slice(0, 5).map(ev => {
                const isEvNegative = ev.type === "Sortie" || ev.type === "retrait"
                return (
                  <div key={ev.id} className="flex items-center justify-between gap-3 text-sm min-h-10">
                    <div className="flex items-center gap-2 min-w-0">
                      <Clock className="h-4 w-4 text-amber-500" />
                      <span className="font-medium truncate max-w-[140px]">{ev.name}</span>
                    </div>
                    <div className="flex flex-col items-end shrink-0">
                      <span className={cn("font-bold whitespace-nowrap tabular-nums", isEvNegative ? "text-slate-900" : "text-emerald-600")}>
                        {isEvNegative ? "-" : "+"}{isPrivacyMode ? "***" : formatCurrency(ev.amount, ev.currency)}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(ev.date).toLocaleDateString(appLocale(), { day: 'numeric', month: 'short' })}
                      </span>
                    </div>
                  </div>
                )
              })}
              {data?.events.filter(e => e.is_projected || e.is_upcoming).length === 0 && (
                <p className="text-xs text-slate-400 text-center py-4">{t("calendarSummary.aucuneEcheancePrevue")}</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">{t("calendarSummary.legendeInfos")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-slate-100 border border-slate-200" />
                <span>{t("calendarSummary.transactionReellePassePresent")}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-amber-50 border border-amber-200" />
                <span>{t("calendarSummary.prevuRecurrentFutur")}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-600" />
                <span>{t("calendarSummary.aujourdHui")}</span>
              </div>
              <div className="mt-4 p-2 bg-slate-50 rounded border border-slate-100 flex gap-2">
                <Info className="h-4 w-4 text-slate-400 shrink-0" />
                <p className="text-slate-500 leading-tight">
                  {t("calendarSummary.lesSoldesQuotidiensIncluentLes")}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {!embedded && <Card className="border-slate-200 flex flex-col justify-center items-center p-6 text-center">
          <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
            <Plus className="h-6 w-6 text-slate-600" />
          </div>
          <h3 className="font-bold text-slate-900">{t("calendarSummary.ajouterUneRecurrence")}</h3>
          <p className="text-sm text-slate-500 mt-1 mb-4">
            {t("calendarSummary.gerezVosRevenusEtCharges")}
          </p>
          <Button variant="outline" size="sm" className="w-full" asChild>
            <Link to="/recurring">{t("calendarSummary.accederAuxRecurrences")}</Link>
          </Button>
        </Card>}
      </div>
    </>
  )
}
