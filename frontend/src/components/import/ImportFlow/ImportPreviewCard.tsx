import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { ImportFlowCtx } from "./useImportFlow"

/** Aperçu des lignes à importer. */
export function ImportPreviewCard({ ctx }: { ctx: ImportFlowCtx }) {
  const preview = ctx.preview!
  return (
    <>
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b">
          <CardTitle className="text-lg">Aperçu des données</CardTitle>
          <CardDescription>Les 20 premières lignes identifiées dans le fichier.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <ul className="divide-y divide-slate-100 md:hidden">
            {preview.preview.map((row, i) => (
              <li key={i} className={`flex items-center justify-between gap-3 px-4 py-3 ${row.error ? "bg-rose-50" : ""}`}>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-slate-900">{row.Commercant}</p>
                  {row.error && <p className="text-xs font-medium text-rose-600">Ligne {row.line} : {row.error}</p>}
                  <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
                    <span>{row.Date}</span>
                    <Badge variant="outline" className="h-5 max-w-[10rem] truncate border-slate-200 py-0 text-[10px] font-bold text-slate-600">{row.Categorie}</Badge>
                  </p>
                </div>
                <span className="shrink-0 whitespace-nowrap text-sm font-black tabular-nums text-slate-900">{row.Montant}€</span>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto md:block">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/50 hover:bg-slate-50/50 border-b border-slate-100">
                  <TableHead className="text-[10px] uppercase font-black tracking-widest text-slate-400">Date</TableHead>
                  <TableHead className="text-[10px] uppercase font-black tracking-widest text-slate-400">Type</TableHead>
                  <TableHead className="text-[10px] uppercase font-black tracking-widest text-slate-400">Commerçant</TableHead>
                  <TableHead className="text-[10px] uppercase font-black tracking-widest text-slate-400">Catégorie</TableHead>
                  <TableHead className="text-right text-[10px] uppercase font-black tracking-widest text-slate-400">Montant</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.preview.map((row, i) => (
                  <TableRow key={i} className={`border-b border-slate-50 transition-colors ${row.error ? "bg-rose-50 hover:bg-rose-50" : "hover:bg-slate-50/30"}`}>
                    <TableCell className="text-xs text-slate-500 font-medium">{row.Date}</TableCell>
                    <TableCell className="text-xs text-slate-500 font-medium">{row.Type}</TableCell>
                    <TableCell className="font-bold text-xs text-slate-900">
                      {row.Commercant}
                      {row.error && <span className="block font-medium text-rose-600">Ligne {row.line} : {row.error}</span>}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] font-bold py-0 h-5 border-slate-200 text-slate-600">
                        {row.Categorie}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-xs font-black text-slate-900">{row.Montant}€</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
