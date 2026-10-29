import { AlertCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { ImportFlowCtx } from "./useImportFlow"

/** Correspondance des catégories du fichier. */
export function CategoryMappingCard({ ctx }: { ctx: ImportFlowCtx }) {
  const { categories, categoryMapping, handleMappingChange, preview } = ctx
  return (
    <>
      {preview && (
         <Card className="shadow-sm border-slate-100 overflow-hidden">
           <CardHeader className="bg-slate-50/50 border-b">
             <CardTitle className="text-sm font-bold">Analyse du fichier</CardTitle>
           </CardHeader>
           <CardContent className="p-4 sm:p-6 space-y-4">
             <div className="flex justify-between items-center">
               <span className="text-sm text-slate-500 font-medium">Lignes totales</span>
               <Badge variant="secondary" className="font-bold">{preview.total_rows}</Badge>
             </div>
             <div className="flex justify-between items-center">
               <span className="text-sm text-slate-500 font-medium">Séparateur</span>
               <code className="bg-slate-100 px-2 py-1 rounded text-xs font-bold">"{preview.delimiter}"</code>
             </div>
             {preview.invalid_rows > 0 && (
               <div className="flex justify-between items-center">
                 <span className="text-sm text-rose-600 font-medium">Lignes invalides (ignorées)</span>
                 <Badge variant="destructive" className="font-bold">{preview.invalid_rows}</Badge>
               </div>
             )}
             {preview.warnings?.map((w, i) => (
               <div key={i} className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
                 <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                 <span>{w}</span>
               </div>
             ))}
             {preview.unknown_categories.length > 0 && (
               <div className="space-y-4 pt-4 border-t">
                 <div className="flex items-center gap-2 text-amber-600">
                   <AlertCircle className="h-4 w-4" />
                   <span className="text-xs font-bold uppercase tracking-wider">Mapping catégories</span>
                 </div>
                 <div className="space-y-3">
                   {preview.unknown_categories.map((csvCat, i) => (
                     <div key={i} className="space-y-1.5 p-3 bg-slate-50 rounded-xl border border-slate-100">
                       <Label className="text-[10px] uppercase text-slate-400 font-black tracking-widest block mb-1">{csvCat}</Label>
                       <Select 
                         value={String(categoryMapping[csvCat])} 
                         onValueChange={(v) => handleMappingChange(csvCat, v)}
                       >
                         <SelectTrigger className="h-11 text-sm bg-white border-slate-200 sm:h-9 sm:text-xs">
                           <SelectValue />
                         </SelectTrigger>
                         <SelectContent>
                           <SelectItem value="CREATE" className="text-emerald-600 font-bold">Créer nouvelle</SelectItem>
                           {categories.map(cat => (
                             <SelectItem key={cat.id} value={String(cat.id)}>{cat.name}</SelectItem>
                           ))}
                         </SelectContent>
                       </Select>
                     </div>
                   ))}
                 </div>
               </div>
             )}
           </CardContent>
         </Card>
      )}
    </>
  )
}
