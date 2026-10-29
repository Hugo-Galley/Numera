import { Clock } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Tableau détaillé des montants par année. */
export function DetailTable({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { data, formatCurrency } = ctx
  return (
    <>
      {/* TABLEAU DETAILLE DES MONTANTS */}
      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm">
        <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex justify-between items-center">
          <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-slate-500" />
            Tableau annuel détaillé
          </span>
          <span className="text-[10px] text-slate-400">Montants nets d'impôts</span>
        </div>
        <div className="max-h-[290px] overflow-y-auto">
          <Table>
            <TableHeader className="bg-slate-50/90 sticky top-0 z-10 shadow-[0_1px_0_rgba(0,0,0,0.05)] backdrop-blur-sm">
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-16 py-1.5 text-[10px] font-bold text-slate-550 uppercase">Année</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Total (Nom.)</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Total (Réel)</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Versements</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Intérêts</TableHead>
                <TableHead className="text-right py-1.5 text-[10px] font-bold text-slate-550 uppercase">Événement</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map((item: any) => (
                <TableRow key={item.year} className="hover:bg-slate-50/50">
                  <TableCell className="font-medium text-[11px] py-1.5">{item.year}</TableCell>
                  <TableCell className="text-right font-semibold text-[11px] py-1.5 amount-blur text-indigo-600">
                    {formatCurrency(item.total_value)}
                  </TableCell>
                  <TableCell className="text-right text-[11px] py-1.5 amount-blur text-slate-655">
                    {formatCurrency(item.total_value_real)}
                  </TableCell>
                  <TableCell className="text-right text-[11px] py-1.5 amount-blur text-slate-500">
                    {formatCurrency(item.total_contributions)}
                  </TableCell>
                  <TableCell className="text-right text-[11px] py-1.5 amount-blur text-emerald-600">
                    {formatCurrency(item.total_interest)}
                  </TableCell>
                  <TableCell className="text-right text-[10px] py-1.5 text-amber-600 max-w-[110px] truncate" title={item.event_applied}>
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
