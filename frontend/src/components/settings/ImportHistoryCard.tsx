import { useEffect, useState } from "react"
import { ChevronDown, ChevronUp, History } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"

type ImportLog = {
  id: number
  source_file: string
  imported_count: number
  skipped_count: number
  error_count: number
  summary_json: string
  created_at: string
}

// Historique des imports CSV (l'import lui-même se lance depuis la page d'un compte)
export function ImportHistoryCard() {
  const [importLogs, setImportLogs] = useState<ImportLog[]>([])
  const [showLogs, setShowLogs] = useState(false)

  useEffect(() => {
    api.get<ImportLog[]>("/import/logs")
      .then((logs) => { if (Array.isArray(logs)) setImportLogs(logs) })
      .catch(() => setImportLogs([]))
  }, [])

  return (
    <Card>
      <CardContent className="space-y-4 p-4 sm:p-6">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-slate-900">
            <History className="h-5 w-5" />
            <h3 className="font-bold text-base sm:text-lg">Historique des importations</h3>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setShowLogs(!showLogs)}
            className="h-10 shrink-0 text-slate-500 hover:text-slate-900"
          >
            {showLogs ? (
              <><ChevronUp className="h-4 w-4 mr-2" /> Masquer</>
            ) : (
              <><ChevronDown className="h-4 w-4 mr-2" /> <span className="sm:hidden">Afficher ({importLogs.length})</span><span className="hidden sm:inline">Afficher les {importLogs.length} dernières</span></>
            )}
          </Button>
        </div>

        {showLogs && (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {importLogs.map((log) => (
              <Card key={log.id} className="shadow-sm border-slate-100 group hover:border-slate-200 transition-all">
                <CardHeader className="p-4 pb-2">
                  <div className="flex justify-between items-start gap-2">
                    <div className="min-w-0">
                      <CardTitle className="text-sm truncate" title={log.source_file}>
                        {log.source_file}
                      </CardTitle>
                      <CardDescription className="text-[10px] uppercase font-bold text-slate-400 mt-1">
                        {new Date(log.created_at).toLocaleString('fr-FR')}
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="text-[9px] font-black h-5 shrink-0">
                      #{log.id}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-2">
                  <div className="grid grid-cols-3 gap-2">
                    <div className="text-center p-2 rounded-lg bg-emerald-50 border border-emerald-100">
                      <p className="text-[9px] font-black text-emerald-600 uppercase">Succès</p>
                      <p className="text-lg font-bold text-emerald-700">{log.imported_count}</p>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-amber-50 border border-amber-100">
                      <p className="text-[9px] font-black text-amber-600 uppercase">Ignorés</p>
                      <p className="text-lg font-bold text-amber-700">{log.skipped_count}</p>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-rose-50 border border-rose-100">
                      <p className="text-[9px] font-black text-rose-600 uppercase">Erreurs</p>
                      <p className="text-lg font-bold text-rose-700">{log.error_count}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {importLogs.length === 0 && (
              <div className="col-span-full py-12 text-center bg-slate-50 rounded-2xl border-2 border-dashed border-slate-100">
                <p className="text-sm text-slate-400 font-medium">Aucune importation enregistrée.</p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
