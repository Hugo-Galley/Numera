import { useTranslation } from "react-i18next"
import { Clock } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Tableau détaillé des montants par année. */
export function DetailTable({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { t } = useTranslation("tools")
  const { data, formatCurrency } = ctx
  return (
    <>
      {/* TABLEAU DETAILLE DES MONTANTS */}
      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-xs">
        <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex justify-between items-center">
          <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-slate-500" />
            {t("detailTable.tableauAnnuelDetaille")}
          </span>
          <span className="text-[10px] text-slate-400">{t("detailTable.montantsNetsDImpots")}</span>
        </div>
        <div className="max-h-[290px] overflow-y-auto">
          <Table>
            <TableHeader className="bg-slate-50/90 sticky top-0 z-10 shadow-[0_1px_0_rgba(0,0,0,0.05)] backdrop-blur-xs">
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-16 py-1.5 text-[10px] font-bold text-slate-550 uppercase">{t("detailTable.annee")}</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">{t("detailTable.totalNom")}</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">{t("detailTable.totalReel")}</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">{t("detailTable.versements")}</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">{t("detailTable.interets")}</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">{t("detailTable.evenement")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map((item) => (
                <TableRow key={item.year} className="hover:bg-slate-50/50">
                  <TableCell className="font-medium text-[11px] py-1.5">{item.year}</TableCell>
                  <TableCell className="text-right font-semibold text-[11px] py-1.5 amount-blur text-indigo-600">
                    {formatCurrency(item.total_value)}
                  </TableCell>
                  <TableCell className="text-right text-[11px] py-1.5 amount-blur text-slate-655">
                    {formatCurrency(item.total_value_real ?? 0)}
                  </TableCell>
                  <TableCell className="text-right text-[11px] py-1.5 amount-blur text-slate-500">
                    {formatCurrency(item.total_contributions)}
                  </TableCell>
                  <TableCell className="text-right text-[11px] py-1.5 amount-blur text-emerald-600">
                    {formatCurrency(item.total_interest)}
                  </TableCell>
                  <TableCell className="text-right text-[10px] py-1.5 text-amber-600 max-w-[110px] truncate" title={item.event_applied ?? undefined}>
                    {item.event_applied || "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </>
  )
}
