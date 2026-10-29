import { Upload } from "lucide-react"
import { ImportFlowProps } from "./types"
import { useImportFlow } from "./useImportFlow"
import { ImportSettingsCard } from "./ImportSettingsCard"
import { CategoryMappingCard } from "./CategoryMappingCard"
import { ImportResultCard } from "./ImportResultCard"
import { ImportPreviewCard } from "./ImportPreviewCard"

export function ImportFlow({ accountId, onImported }: ImportFlowProps) {
  const ctx = useImportFlow(accountId, onImported)
  const { preview, result } = ctx
  return (
    <div className="grid gap-6 md:gap-8 grid-cols-1 lg:grid-cols-3">
      <div className="lg:col-span-1 space-y-6">
        <ImportSettingsCard ctx={ctx} />

        <CategoryMappingCard ctx={ctx} />
      </div>

      <div className="lg:col-span-2 space-y-6">
        {result ? (
          <ImportResultCard ctx={ctx} />
        ) : preview ? (
          <ImportPreviewCard ctx={ctx} />
        ) : (
          <div className="h-full min-h-[220px] md:min-h-[400px] flex flex-col items-center justify-center p-8 md:p-12 text-center border-2 border-dashed rounded-3xl bg-slate-50/50 border-slate-200">
            <div className="h-16 w-16 bg-white rounded-2xl flex items-center justify-center shadow-sm border border-slate-100 mb-6">
              <Upload className="h-8 w-8 text-slate-300" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Aucun fichier en attente</h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto mt-2 font-medium">
              Veuillez sélectionner un fichier CSV sur la gauche pour commencer l'analyse et l'importation.
            </p>
          </div>
        )}
      </div>

    </div>
  )
}
