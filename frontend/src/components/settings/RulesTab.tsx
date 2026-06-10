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

export function RulesTab() {
  const [rules, setRules] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<any>(null)
  
  const [newRule, setNewRule] = useState({
    pattern: "",
    category_id: "",
    merchant_name: "",
    transaction_type: "Sortie",
    priority: 0
  })

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [r, cats] = await Promise.all([
        api.get<any[]>("/categorization-rules/"),
        api.get<any[]>("/categories")
      ])
      setRules(r)
      setCategories(cats)
    } catch (error) {
      console.error("Failed to load rules", error)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate() {
    if (!newRule.pattern) return
    try {
      await api.post("/categorization-rules/", {
        ...newRule,
        category_id: newRule.category_id ? parseInt(newRule.category_id) : null
      })
      toast.success("Règle créée avec succès")
      setIsAddOpen(false)
      setNewRule({
        pattern: "",
        category_id: "",
        merchant_name: "",
        transaction_type: "Sortie",
        priority: 0
      })
      loadData()
    } catch (error) {
      toast.error("Échec de la création")
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Supprimer cette règle ?")) return
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Règles d'auto-catégorisation</h3>
          <p className="text-sm text-slate-500 mt-1">Définissez des règles pour automatiser le tri de vos transactions lors de l'import.</p>
        </div>
        <div className="flex gap-2">
           <Button variant="outline" size="sm" className="gap-2" onClick={handleApplyAll}>
             <RefreshCw className="h-4 w-4" />
             Appliquer à l'existant
           </Button>
           <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
             <DialogTrigger asChild>
               <Button size="sm" className="gap-2">
                 <Plus className="h-4 w-4" />
                 Nouvelle règle
               </Button>
             </DialogTrigger>
             <DialogContent className="sm:max-w-[425px]">
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
                          <SelectItem value="Sortie">Sortie</SelectItem>
                          <SelectItem value="Entree">Entrée</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-bold">Priorité</label>
                      <Input 
                        type="number" 
                        value={newRule.priority}
                        onChange={e => setNewRule({...newRule, priority: parseInt(e.target.value) || 0})}
                      />
                    </div>
                 </div>
               </div>
               <DialogFooter>
                 <Button variant="outline" onClick={() => setIsAddOpen(false)}>Annuler</Button>
                 <Button onClick={handleCreate}>Créer la règle</Button>
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
                <div key={rule.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 bg-slate-100 rounded-xl flex items-center justify-center text-slate-500 shadow-sm">
                      <Filter className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-bold text-slate-900 flex items-center gap-2">
                        {rule.pattern}
                        <ArrowRight className="h-3 w-3 text-slate-400" />
                        {rule.merchant_name || rule.pattern}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        {category && (
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 border-slate-200">
                             <div className="h-1.5 w-1.5 rounded-full mr-1.5" style={{ backgroundColor: category.color }} />
                             {category.name}
                          </Badge>
                        )}
                        <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Priorité: {rule.priority}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50" onClick={() => handleDelete(rule.id)}>
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
           Les règles sont appliquées dans l'ordre de **priorité** décroissante. La première règle qui correspond à une transaction arrête le processus pour cette transaction.
         </p>
      </div>
    </div>
  )
}
