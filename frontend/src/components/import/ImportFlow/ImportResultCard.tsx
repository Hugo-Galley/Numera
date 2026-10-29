import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2 } from "lucide-react"
import type { ImportFlowCtx } from "./useImportFlow"

/** Résultat de l'import. */
export function ImportResultCard({ ctx }: { ctx: ImportFlowCtx }) {
  const { result } = ctx
  return (
    <>
      <Card className="border-emerald-200 bg-emerald-50/20 shadow-sm overflow-hidden">
        <CardHeader className="border-b border-emerald-100 bg-emerald-50/50">
          <div className="flex items-center gap-2 text-emerald-600">
            <CheckCircle2 className="h-5 w-5" />
            <CardTitle className="text-lg">
              {result.imported === 0 && result.errors > 0 ? "Aucune ligne importée" : result.errors > 0 ? "Importation partielle" : "Importation réussie"}
            </CardTitle>
          </div>
          <CardDescription className="text-emerald-600/70">
            {result.errors > 0 ? "Certaines lignes n'ont pas pu être importées (détail ci-dessous)." : "Les données ont été traitées avec succès."}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-4 sm:p-6 grid gap-3 sm:gap-4 grid-cols-3">
          <div className="bg-white p-3 sm:p-4 rounded-2xl border border-emerald-100 shadow-sm">
            <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Transactions</p>
            <p className="text-2xl sm:text-3xl font-extrabold text-emerald-600 mt-1">{result.imported}</p>
          </div>
          <div className="bg-white p-3 sm:p-4 rounded-2xl border border-amber-100 shadow-sm">
            <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Doublons</p>
            <p className="text-2xl sm:text-3xl font-extrabold text-amber-500 mt-1">{result.skipped}</p>
          </div>
          <div className="bg-white p-3 sm:p-4 rounded-2xl border border-rose-100 shadow-sm">
            <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Erreurs</p>
            <p className="text-2xl sm:text-3xl font-extrabold text-rose-500 mt-1">{result.errors}</p>
          </div>
          {result.error_details?.length > 0 && (
            <ul className="col-span-3 space-y-1 rounded-2xl border border-rose-100 bg-white p-3 text-xs text-slate-700">
              {result.error_details.map((d: { line: number; reason: string }, i: number) => (
                <li key={i}><span className="font-bold text-rose-500">Ligne {d.line}</span> — {d.reason}</li>
              ))}
              {result.errors > result.error_details.length && (
                <li className="text-slate-400">… et {result.errors - result.error_details.length} autre(s)</li>
              )}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  )
}
