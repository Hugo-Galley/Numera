import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { FileText, Upload } from "lucide-react"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { accountTypeLabel } from "@/lib/labels"
import type { ImportFlowCtx } from "./useImportFlow"

/** Choix du compte et du fichier. */
export function ImportSettingsCard({ ctx }: { ctx: ImportFlowCtx }) {
  const { accountId, accounts, createMissingCategories, file, handleFileChange, handleImport, importing, selectedAccountId, setCreateMissingCategories, setSelectedAccountId } = ctx
  return (
    <>
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b">
          <CardTitle className="text-lg">Source des données</CardTitle>
          <CardDescription>Sélectionnez le compte et le fichier CSV.</CardDescription>
        </CardHeader>
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Compte de destination</Label>
            {accountId ? (
              <p className="flex h-11 items-center rounded-md border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-900 sm:h-10">
                {accounts.find((acc) => acc.id === accountId)?.name ?? "…"}
              </p>
            ) : (
            <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
              <SelectTrigger className="h-11 bg-slate-50 border-slate-200 sm:h-10">
                <SelectValue placeholder="Choisir un compte" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((acc) => (
                  <SelectItem key={acc.id} value={String(acc.id)}>
                    {acc.name} ({accountTypeLabel(acc.type)})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Fichier CSV</Label>
            <div className="flex items-center justify-center w-full">
              <label className="flex flex-col items-center justify-center w-full h-36 sm:h-32 border-2 border-dashed rounded-xl cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors border-slate-200">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <Upload className="w-8 h-8 mb-3 text-slate-400" />
                  <p className="mb-2 text-sm text-slate-500">
                    <span className="font-semibold text-center px-4"><span className="md:hidden">Touchez pour choisir un fichier</span><span className="hidden md:inline">Cliquez pour uploader</span></span>
                  </p>
                  <p className="text-xs text-slate-400">CSV (format Numbers)</p>
                </div>
                <input type="file" className="hidden" accept=".csv" onChange={handleFileChange} />
              </label>
            </div>
            {file && (
              <div className="flex items-center gap-2 p-2 bg-slate-100 rounded-lg">
                <FileText className="h-4 w-4 text-slate-500" />
                <p className="text-xs text-slate-600 font-medium truncate italic">{file.name}</p>
              </div>
            )}
          </div>

          <div className="flex min-h-10 items-center space-x-3 pt-2">
            <Checkbox 
              id="categories" 
              checked={createMissingCategories} 
              onCheckedChange={(checked) => setCreateMissingCategories(!!checked)} 
            />
            <Label htmlFor="categories" className="text-xs font-bold text-slate-700 cursor-pointer">
              Créer les catégories manquantes
            </Label>
          </div>

          <Button 
            className="w-full bg-slate-900 text-white hover:bg-slate-800 shadow-lg mt-4 h-12 rounded-xl" 
            disabled={!file || !selectedAccountId || importing}
            onClick={handleImport}
          >
            {importing ? "Importation en cours..." : "Lancer l'importation"}
          </Button>
        </CardContent>
      </Card>
    </>
  )
}
