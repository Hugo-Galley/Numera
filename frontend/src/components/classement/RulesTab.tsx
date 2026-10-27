import { useEffect, useState } from "react"
import {
  Plus,
  Trash2,
  Pencil,
  Tag,
  AlertCircle,
  RefreshCw,
  Search,
  ChevronRight,
  Filter,
  ArrowRight
} from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"

export function RulesTab() {
  const confirm = useConfirm()
  const [rules, setRules] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<any>(null)
  
  const [newRule, setNewRule] = useState({
    pattern: "",
    category_id: "",
    merchant_name: "",
    transaction_type: "none", // "none" = ne change pas le type de la transaction
    priority: 0
  })

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [r, cats] = await Promise.all([
        api.get<any[]>("/categorization-rules/"),
        api.get<any[]>("/categories?include_archived=false")
      ])
      setRules(r)
      setCategories(cats)
    } catch (error) {
      console.error("Failed to load rules", error)
      toast.error("Impossible de charger les règles")
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate() {
    if (!newRule.pattern) return
    try {
      await api.post("/categorization-rules/", {
        ...newRule,
        category_id: newRule.category_id ? parseInt(newRule.category_id) : null,
        transaction_type: newRule.transaction_type === "none" ? null : newRule.transaction_type,
      })
      toast.success("Règle créée avec succès")
      setIsAddOpen(false)
      setNewRule({
        pattern: "",
        category_id: "",
        merchant_name: "",
        transaction_type: "none", // "none" = ne change pas le type de la transaction
        priority: 0
      })
      loadData()
    } catch (error) {
      toast.error("Échec de la création")
    }
  }

  async function handleDelete(id: number) {
    if (!(await confirm("Supprimer cette règle ?"))) return
    try {
      await api.delete(`/categorization-rules/${id}`)
      toast.success("Règle supprimée")
      loadData()
    } catch (error) {
      toast.error("Échec de la suppression")
    }
  }

  async function handleApplyAll() {
    try {
      const res = await api.post<any>("/categorization-rules/apply-all", {})
      toast.success(`${res.modified_count} transactions mises à jour`)
    } catch (error) {
      toast.error("Échec de l'application des règles")
    }
  }

  if (loading) return <div className="p-8 text-center text-slate-500">Chargement...</div>

  return (
    <div className="space-y-6 [&_input]:text-base md:[&_input]:text-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Règles d'auto-catégorisation</h3>
          <p className="text-sm text-slate-500 mt-1">Définissez des règles pour automatiser le tri de vos transactions lors de l'import.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex">
           <Button variant="outline" size="sm" className="h-11 gap-2 sm:h-9" onClick={handleApplyAll}>
             <RefreshCw className="h-4 w-4" />
             Appliquer à l'existant
           </Button>
           <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
             <DialogTrigger asChild>
               <Button size="sm" className="h-11 w-full gap-2 sm:h-9 sm:w-auto">
                 <Plus className="h-4 w-4" />
                 Nouvelle règle
               </Button>
             </DialogTrigger>
             <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[425px]">
               <DialogHeader>
                 <DialogTitle>Ajouter une règle</DialogTitle>
                 <DialogDescription>
                   Les transactions dont le marchand ou la note contient ce texte seront automatiquement modifiées.
                 </DialogDescription>
               </DialogHeader>
               <div className="grid gap-4 py-4">
                 <div className="space-y-2">
                   <label className="text-sm font-bold">Mot-clé (Pattern)</label>
                   <Input 
                     placeholder="Ex: Uber, Netflix, Carrefour..." 
                     value={newRule.pattern}
                     onChange={e => setNewRule({...newRule, pattern: e.target.value})}
                   />
                 </div>
                 <div className="space-y-2">
                   <label className="text-sm font-bold">Catégorie cible</label>
                   <Select 
                     value={newRule.category_id} 
                     onValueChange={v => setNewRule({...newRule, category_id: v})}
                   >
                     <SelectTrigger>
                       <SelectValue placeholder="Choisir une catégorie" />
                     </SelectTrigger>
                     <SelectContent>
                       {categories.map(c => (
                         <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                       ))}
                     </SelectContent>
                   </Select>
                 </div>
                 <div className="space-y-2">
                   <label className="text-sm font-bold">Renommer le marchand (Optionnel)</label>
                   <Input 
                     placeholder="Nom propre du marchand" 
                     value={newRule.merchant_name}
                     onChange={e => setNewRule({...newRule, merchant_name: e.target.value})}
                   />
                 </div>
                 <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-bold">Type</label>
                      <Select 
                        value={newRule.transaction_type} 
                        onValueChange={v => setNewRule({...newRule, transaction_type: v})}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Aucun changement</SelectItem>
                          <SelectItem value="Sortie">Forcer en Sortie</SelectItem>
                          <SelectItem value="Entree">Forcer en Entrée</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-bold">Priorité</label>
                      <Input 
                        type="number" inputMode="decimal" 
                        value={newRule.priority}
                        onChange={e => setNewRule({...newRule, priority: parseInt(e.target.value) || 0})}
                      />
                    </div>
                 </div>
               </div>
               <DialogFooter className="gap-2 sm:gap-0">
                 <Button variant="outline" className="h-11 sm:h-10" onClick={() => setIsAddOpen(false)}>Annuler</Button>
                 <Button className="h-11 sm:h-10" onClick={handleCreate}>Créer la règle</Button>
               </DialogFooter>
             </DialogContent>
           </Dialog>
        </div>
      </div>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardContent className="p-0">
          <div className="divide-y">
            {rules.map((rule) => {
              const category = categories.find(c => c.id === rule.category_id)
              return (
                <div key={rule.id} className="p-4 flex items-center justify-between gap-2 hover:bg-slate-50 transition-colors">
                  <div className="flex min-w-0 items-center gap-3 sm:gap-4">
                    <div className="h-10 w-10 shrink-0 bg-slate-100 rounded-xl flex items-center justify-center text-slate-500 shadow-sm">
                      <Filter className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-bold text-slate-900 flex min-w-0 items-center gap-2">
                        <span className="truncate">{rule.pattern}</span>
                        <ArrowRight className="h-3 w-3 shrink-0 text-slate-400" />
                        <span className="truncate">{rule.merchant_name || rule.pattern}</span>
                      </p>
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-0.5">
                        {category && (
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 border-slate-200">
                             <div className="h-1.5 w-1.5 rounded-full mr-1.5" style={{ backgroundColor: category.color }} />
                             {category.name}
                          </Badge>
                        )}
                        {rule.transaction_type && (
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 border-amber-200 text-amber-700">
                            Type → {rule.transaction_type === "Entree" ? "Entrée" : rule.transaction_type}
                          </Badge>
                        )}
                        <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Priorité: {rule.priority}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Button aria-label="Supprimer" variant="ghost" size="sm" className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50" onClick={() => handleDelete(rule.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )
            })}
            {rules.length === 0 && (
              <div className="p-12 text-center text-slate-400 italic bg-slate-50/50">
                Aucune règle définie. Automatisez votre gestion en créant votre première règle.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
      
      <div className="p-4 bg-amber-50 rounded-xl border border-amber-100 flex gap-3">
         <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
         <p className="text-xs text-amber-800 leading-relaxed">
           Les règles sont appliquées dans l'ordre de <strong>priorité</strong> décroissante. La première règle qui correspond à une transaction arrête le processus pour cette transaction.
         </p>
      </div>
    </div>
  )
}
