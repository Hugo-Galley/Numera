import { useTranslation } from "react-i18next"
import { dateLocale } from "@/i18n/locale"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, Download, Wallet } from "lucide-react"
import { format } from "date-fns"
import { formatCurrency } from "@/lib/utils"
import type { SalaryManagerCtx } from "./useSalaryManager"

/** Synthèse du mois : salaire calculé, tickets et génération. */
export function MonthSummaryPanel({ ctx }: { ctx: SalaryManagerCtx }) {
  const { t } = useTranslation("tools")
  const { config, currentDate, generating, handleGenerate, handleReset, isGenerated, monthLoadFailed, nbTickets, salaryDate, summary } = ctx
  return (
    <>
      <div className="lg:col-span-1">
        <Card className="h-full flex flex-col shadow-md">
          <CardHeader className="border-b pb-4">
            <CardTitle className="text-lg flex flex-wrap gap-x-3 justify-between items-center">
              <span className="flex items-center gap-2">
                <Wallet className="h-5 w-5 text-primary" />
                {t("monthSummaryPanel.resumeDuMois")}
              </span>
              <span className="text-sm font-medium text-muted-foreground">
                {format(currentDate, "MMMM yyyy", { locale: dateLocale() })}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 flex-1 flex flex-col">
            <div className="space-y-6 flex-1">

              {/* Banque */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  {t("monthSummaryPanel.recuEnBanque")}
                </h3>
                <div className="bg-muted/50 border rounded-xl p-4 text-sm shadow-inner">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-muted-foreground">{t("monthSummaryPanel.salaireNetApresPrimes")}</span>
                    <span className="font-medium">{summary ? formatCurrency(summary.net_salary) : "—"}</span>
                  </div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="min-w-0 text-muted-foreground">{t("misc.mealDeduction", { count: nbTickets, amount: formatCurrency(config.ticket_employee_share) })}</span>
                    <span className="text-destructive font-medium whitespace-nowrap tabular-nums">- {summary ? formatCurrency(summary.ticket_deduction) : "—"}</span>
                  </div>
                  <div className="border-t pt-3 flex justify-between items-center">
                    <span className="font-bold">{t("monthSummaryPanel.totalVerse")}</span>
                    <span className="font-black text-xl text-emerald-600 whitespace-nowrap tabular-nums">{summary ? formatCurrency(summary.real_salary) : "—"}</span>
                  </div>
                </div>
              </div>

              {/* TR */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  {t("monthSummaryPanel.titresRestaurantIndicatif")}
                </h3>
                <div className="bg-muted/50 border rounded-xl p-4 text-sm shadow-inner">
                  <p className="text-xs text-muted-foreground mb-2 italic">
                    {t("monthSummaryPanel.ceMontantNEstPas")}
                  </p>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">{t("misc.mealCredited", { count: nbTickets, amount: formatCurrency(config.ticket_value) })}</span>
                    <span className="font-black text-xl text-amber-500 whitespace-nowrap tabular-nums">+ {summary ? formatCurrency(summary.ticket_credit) : "—"}</span>
                  </div>
                </div>
              </div>

            </div>

            <div className="mt-6 pt-5 md:mt-8 md:pt-6 border-t">
              {isGenerated ? (
                <div className="flex flex-col gap-3">
                  <div className="bg-emerald-100 border border-emerald-200 text-emerald-700 p-4 rounded-xl flex items-center justify-center gap-2 font-medium shadow-xs">
                    <CheckCircle2 className="h-5 w-5" />
                    {t("monthSummaryPanel.salaireDuMoisGenere")}
                  </div>
                  <Button variant="outline" className="h-11 w-full md:h-9" onClick={handleReset}>
                    {t("monthSummaryPanel.reinitialiserCeMois")}
                  </Button>
                </div>
              ) : (
                <Button 
                  className="w-full h-12 text-base font-bold shadow-lg transition-transform hover:scale-[1.02]" 
                  onClick={handleGenerate}
                  disabled={generating || !salaryDate || monthLoadFailed}
                >
                  {generating ? t("monthSummaryPanel.generation") : <><Download className="mr-2 h-5 w-5" /> {t("monthSummaryPanel.genererLesTransactions")}</>}
                </Button>
              )}
              {!salaryDate && !isGenerated && (
                <p className="text-xs text-center text-slate-400 mt-3 font-medium">
                  {t("monthSummaryPanel.veuillezDefinirUneDateDe")}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
