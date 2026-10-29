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
  const { loadingReport, report, setYear, year, years } = ctx
  return (
    <>
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-xl font-semibold"><FileText className="h-5 w-5" /> Déclaration</h2>
          <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
            <SelectTrigger className="w-32" aria-label="Année de déclaration"><SelectValue /></SelectTrigger>
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
              Aucun compte CTO configuré.
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
                      <span className="shrink-0 text-xs text-slate-500">{row.sales} cession{row.sales > 1 ? "s" : ""}</span>
                    </div>
                    <dl className="mt-2 grid grid-cols-2 gap-3 border-t pt-2 text-xs">
                      <div>
                        <dt className="text-slate-500">Dividendes bruts (2DC)</dt>
                        <dd className="mt-0.5 text-sm font-semibold"><Money value={row.dividends_gross_eur} /></dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Plus-values réalisées</dt>
                        <dd className="mt-0.5 text-sm font-semibold"><Money value={row.realized_eur} /></dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ul>
              <Table className="hidden md:table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Compte</TableHead>
                    <TableHead className="text-right">Dividendes bruts (2DC)</TableHead>
                    <TableHead className="text-right">Plus-values réalisées</TableHead>
                    <TableHead className="text-right">Cessions</TableHead>
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
                <div><dt className="text-slate-500">Case 2DC (dividendes)</dt><dd className="text-lg font-semibold"><Money value={report.box_2dc} /></dd></div>
                <div><dt className="text-slate-500">Case 3VG (plus-values)</dt><dd className="text-lg font-semibold"><Money value={report.box_3vg} /></dd></div>
                <div><dt className="text-slate-500">Case 3VH (moins-values)</dt><dd className="text-lg font-semibold"><Money value={report.box_3vh} /></dd></div>
                <div className="col-span-2 lg:col-span-1">
                  <dt className="text-slate-500">
                    Impôt estimé (PFU {formatRate(report.pfu_rate_dividends * 100, 1)} dividendes, {formatRate(report.pfu_rate_gains * 100, 1)} plus-values)
                  </dt>
                  <dd className="text-lg font-semibold"><Money value={report.estimated_pfu_eur} /></dd>
                </div>
              </dl>
              <p className="text-xs text-slate-500">Estimation indicative : ne remplace pas ta déclaration.</p>
            </CardContent>
          </Card>
        )}
      </section>
    </>
  )
}
