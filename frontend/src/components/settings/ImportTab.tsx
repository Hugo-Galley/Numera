import { useState, useEffect } from "react"
import { 
  Upload, 
  FileText, 
  CheckCircle2, 
  AlertCircle,
  Info,
  History,
  ChevronDown,
  ChevronUp
} from "lucide-react"
import { api, API_BASE } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"

type Account = {
  id: number
  name: string
  type: string
  active: boolean
}

type Category = {
  id: number
  name: string
}

type PreviewData = {
  filename: string
  total_rows: number
  delimiter: string
  preview: any[]
  unknown_categories: string[]
}

type ImportLog = {
  id: number
  source_file: string
  imported_count: number
  skipped_count: number
  error_count: number
  summary_json: string
  created_at: string
}

export function ImportTab() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [importLogs, setImportLogs] = useState<ImportLog[]>([])
  const [showLogs, setShowLogs] = useState(false)
  const [selectedAccountId, setSelectedAccountId] = useState<string>("")
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [createMissingCategories, setCreateMissingCategories] = useState(true)
  const [categoryMapping, setCategoryMapping] = useState<Record<string, string | number>>({})
  const [result, setResult] = useState<any | null>(null)

  const loadInitialData = async () => {
    try {
      const [accs, cats, logs] = await Promise.all([
        api.get<Account[]>("/accounts"),
        api.get<Category[]>("/categories"),
        api.get<ImportLog[]>("/import/logs")
      ])
      
      if (accs && Array.isArray(accs)) {
        setAccounts(accs.filter((account) => account.active))
      }
      if (cats && Array.isArray(cats)) {
        setCategories(cats)
      }
      if (logs && Array.isArray(logs)) {
        setImportLogs(logs)
      }
    } catch (error) {
      toast.error("Erreur chargement données initiales")
    }
  }

  useEffect(() => {
    loadInitialData()
  }, [])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return
    setFile(selectedFile)
    setPreview(null)
    setResult(null)
    setCategoryMapping({})

    const formData = new FormData()
    formData.append("file", selectedFile)

    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/import/preview`, { method: "POST", body: formData })
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: "Erreur serveur" }))
        toast.error(err.detail || "Erreur lors de l'analyse")
        return
      }
      const data = await r.json()
      setPreview(data)
      
      // Initialize mapping with default behavior (CREATE)
      const initialMapping: Record<string, string> = {}
      data.unknown_categories.forEach((cat: string) => {
        initialMapping[cat] = "CREATE"
      })
      setCategoryMapping(initialMapping)
    } catch (error) {
      toast.error("Erreur lors de l'analyse du fichier")
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!file || !selectedAccountId) return

    const formData = new FormData()
    formData.append("file", file)
    formData.append("account_id", selectedAccountId)
    formData.append("create_missing_categories", String(createMissingCategories))
    formData.append("category_mapping", JSON.stringify(categoryMapping))

    setImporting(true)
    try {
      const r = await fetch(`${API_BASE}/import/commit`, { method: "POST", body: formData })
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: "Erreur serveur" }))
        toast.error(err.detail || "Erreur lors de l'importation")
        return
      }
      const data = await r.json()
      setResult(data)
      toast.success("Import terminé avec succès")
      // Refresh logs
      api.get<ImportLog[]>("/import/logs").then(logs => {
        if (logs && Array.isArray(logs)) setImportLogs(logs)
      })
    } catch (error) {
      toast.error("Erreur lors de l'importation")
    } finally {
      setImporting(false)
    }
  }

  const handleMappingChange = (csvCat: string, value: string) => {
    setCategoryMapping(prev => ({
      ...prev,
      [csvCat]: value === "CREATE" ? "CREATE" : Number(value)
    }))
  }

  return (
    <div className="grid gap-8 grid-cols-1 lg:grid-cols-3">
      <div className="lg:col-span-1 space-y-6">
        <Card className="shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b">
            <CardTitle className="text-lg">Source des données</CardTitle>
            <CardDescription>Sélectionnez le compte et le fichier CSV.</CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Compte de destination</Label>
              <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
                <SelectTrigger className="bg-slate-50 border-slate-200">
                  <SelectValue placeholder="Choisir un compte" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((acc) => (
                    <SelectItem key={acc.id} value={String(acc.id)}>
                      {acc.name} ({acc.type})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Fichier CSV</Label>
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-xl cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors border-slate-200">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-8 h-8 mb-3 text-slate-400" />
                    <p className="mb-2 text-sm text-slate-500">
                      <span className="font-semibold text-center px-4">Cliquez pour uploader</span>
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

            <div className="flex items-center space-x-2 pt-2">
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

        {preview && (
           <Card className="shadow-sm border-slate-100 overflow-hidden">
             <CardHeader className="bg-slate-50/50 border-b">
               <CardTitle className="text-sm font-bold">Analyse du fichier</CardTitle>
             </CardHeader>
             <CardContent className="p-6 space-y-4">
               <div className="flex justify-between items-center">
                 <span className="text-sm text-slate-500 font-medium">Lignes totales</span>
                 <Badge variant="secondary" className="font-bold">{preview.total_rows}</Badge>
               </div>
               <div className="flex justify-between items-center">
                 <span className="text-sm text-slate-500 font-medium">Séparateur</span>
                 <code className="bg-slate-100 px-2 py-1 rounded text-xs font-bold">"{preview.delimiter}"</code>
               </div>
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
                           <SelectTrigger className="h-9 text-xs bg-white border-slate-200">
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
      </div>

      <div className="lg:col-span-2 space-y-6">
        {result ? (
          <Card className="border-emerald-200 bg-emerald-50/20 shadow-sm overflow-hidden">
            <CardHeader className="border-b border-emerald-100 bg-emerald-50/50">
              <div className="flex items-center gap-2 text-emerald-600">
                <CheckCircle2 className="h-5 w-5" />
                <CardTitle className="text-lg">Importation réussie</CardTitle>
              </div>
              <CardDescription className="text-emerald-600/70">Les données ont été traitées avec succès.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 grid gap-4 grid-cols-1 sm:grid-cols-3">
              <div className="bg-white p-4 rounded-2xl border border-emerald-100 shadow-sm">
                <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Transactions</p>
                <p className="text-3xl font-extrabold text-emerald-600 mt-1">{result.imported}</p>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-amber-100 shadow-sm">
                <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Doublons</p>
                <p className="text-3xl font-extrabold text-amber-500 mt-1">{result.skipped}</p>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-rose-100 shadow-sm">
                <p className="text-[10px] uppercase font-black text-slate-400 tracking-widest">Erreurs</p>
                <p className="text-3xl font-extrabold text-rose-500 mt-1">{result.errors}</p>
              </div>
            </CardContent>
          </Card>
        ) : preview ? (
          <Card className="shadow-sm border-slate-100 overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b">
              <CardTitle className="text-lg">Aperçu des données</CardTitle>
              <CardDescription>Les 20 premières lignes identifiées dans le fichier.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50/50 hover:bg-slate-50/50 border-b border-slate-100">
                      <TableHead className="text-[10px] uppercase font-black tracking-widest text-slate-400">Date</TableHead>
                      <TableHead className="text-[10px] uppercase font-black tracking-widest text-slate-400">Commerçant</TableHead>
                      <TableHead className="text-[10px] uppercase font-black tracking-widest text-slate-400">Catégorie</TableHead>
                      <TableHead className="text-right text-[10px] uppercase font-black tracking-widest text-slate-400">Montant</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.preview.map((row, i) => (
                      <TableRow key={i} className="hover:bg-slate-50/30 border-b border-slate-50 transition-colors">
                        <TableCell className="text-xs text-slate-500 font-medium">{row.Date}</TableCell>
                        <TableCell className="font-bold text-xs text-slate-900">{row.Commercant}</TableCell>
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
        ) : (
          <div className="h-full min-h-[400px] flex flex-col items-center justify-center p-12 text-center border-2 border-dashed rounded-3xl bg-slate-50/50 border-slate-200">
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

      <div className="lg:col-span-3 space-y-6 pt-4 border-t">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-900">
            <History className="h-5 w-5" />
            <h3 className="font-bold text-lg">Historique des importations</h3>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setShowLogs(!showLogs)}
            className="text-slate-500 hover:text-slate-900"
          >
            {showLogs ? (
              <><ChevronUp className="h-4 w-4 mr-2" /> Masquer</>
            ) : (
              <><ChevronDown className="h-4 w-4 mr-2" /> Afficher les {importLogs.length} dernières</>
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
      </div>
    </div>
  )
}
