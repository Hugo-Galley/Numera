import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { AlertTriangle, FileText } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatRate } from "@/lib/utils"
import { Money } from "./TaxWidgets"
import type { TaxCtx } from "./useTax"

/** Récapitulatif fiscal annuel par compte. */
export function AnnualReportSection({ ctx }: { ctx: TaxCtx }) {
  const { t } = useTranslation("tax")
  const { loadingReport, report, setYear, year, years } = ctx
  return (
    <>
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-xl font-semibold"><FileText className="h-5 w-5" /> {t("annualReportSection.declaration")}</h2>
          <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
            <SelectTrigger className="w-32" aria-label={t("annualReportSection.anneeDeDeclaration")}><SelectValue /></SelectTrigger>
            <SelectContent>
              {years.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        {loadingReport || !report ? (
          <Skeleton className="h-40" />
        ) : report.accounts.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-slate-600">
              {t("annualReportSection.aucunCompteCtoConfigure")}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="space-y-4 pt-6">
              {report.warnings.map((warning) => (
                <div key={warning} className="flex items-start gap-2 rounded-md bg-amber-50 p-2 text-sm text-amber-800">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{warning}</span>
                </div>
              ))}
              <ul className="space-y-2 md:hidden">
                {report.accounts.map((row) => (
                  <li key={row.account_id} className="rounded-lg border p-3 text-sm">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="min-w-0 break-words font-medium">{row.account_name}</span>
                      <span className="shrink-0 text-xs text-slate-500">{i18n.t("misc.sales", { ns: "tax", count: row.sales })}</span>
                    </div>
                    <dl className="mt-2 grid grid-cols-2 gap-3 border-t pt-2 text-xs">
                      <div>
                        <dt className="text-slate-500">{t("annualReportSection.dividendesBruts2dc")}</dt>
                        <dd className="mt-0.5 text-sm font-semibold"><Money value={row.dividends_gross_eur} /></dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">{t("annualReportSection.plusValuesRealisees")}</dt>
                        <dd className="mt-0.5 text-sm font-semibold"><Money value={row.realized_eur} /></dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ul>
              <Table className="hidden md:table">
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("annualReportSection.compte")}</TableHead>
                    <TableHead className="text-right">{t("annualReportSection.dividendesBruts2dc")}</TableHead>
                    <TableHead className="text-right">{t("annualReportSection.plusValuesRealisees")}</TableHead>
                    <TableHead className="text-right">{t("annualReportSection.cessions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.accounts.map((row) => (
                    <TableRow key={row.account_id}>
                      <TableCell className="font-medium">{row.account_name}</TableCell>
                      <TableCell className="text-right"><Money value={row.dividends_gross_eur} /></TableCell>
                      <TableCell className="text-right"><Money value={row.realized_eur} /></TableCell>
                      <TableCell className="text-right">{row.sales}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <dl className="grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
                <div><dt className="text-slate-500">{t("annualReportSection.case2dcDividendes")}</dt><dd className="text-lg font-semibold"><Money value={report.box_2dc} /></dd></div>
                <div><dt className="text-slate-500">{t("annualReportSection.case3vgPlusValues")}</dt><dd className="text-lg font-semibold"><Money value={report.box_3vg} /></dd></div>
                <div><dt className="text-slate-500">{t("annualReportSection.case3vhMoinsValues")}</dt><dd className="text-lg font-semibold"><Money value={report.box_3vh} /></dd></div>
                <div className="col-span-2 lg:col-span-1">
                  <dt className="text-slate-500">
                    {i18n.t("misc.estimatedTax", { ns: "tax", dividends: formatRate(report.pfu_rate_dividends * 100, 1), gains: formatRate(report.pfu_rate_gains * 100, 1) })}
                  </dt>
                  <dd className="text-lg font-semibold"><Money value={report.estimated_pfu_eur} /></dd>
                </div>
              </dl>
              <p className="text-xs text-slate-500">{t("annualReportSection.estimationIndicativeNeRemplacePas")}</p>
            </CardContent>
          </Card>
        )}
      </section>
    </>
  )
}
