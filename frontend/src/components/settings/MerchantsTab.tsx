import { useState, useEffect } from "react"
import { 
  Plus, 
  ShoppingBag, 
  Pencil, 
  Trash2, 
  Tag as TagIcon, 
  Search, 
  Wand2, 
  AlertCircle,
  PlusCircle,
  X
} from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type MerchantAlias = {
  id: number
  merchant_id: number
  label: string
}

type Merchant = {
  id: number
  name: string
  category_id: number | null
  icon: string | null
  color: string | null
  aliases: MerchantAlias[]
}

type Category = {
  id: number
  name: string
  color?: string
}

type Suggestion = {
  label: string
  count: number
}

const COLOR_OPTIONS = [
  { name: "Emerald", value: "#10b981" },
  { name: "Blue", value: "#3b82f6" },
  { name: "Indigo", value: "#6366f1" },
  { name: "Violet", value: "#8b5cf6" },
  { name: "Pink", value: "#ec4899" },
  { name: "Rose", value: "#f43f5e" },
  { name: "Orange", value: "#f97316" },
  { name: "Amber", value: "#f59e0b" },
  { name: "Slate", value: "#64748b" },
  { name: "Black", value: "#0f172a" },
]

export function MerchantsTab() {
  const [merchants, setMerchants] = useState<Merchant[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")

  // -- New Merchant Form --
  const [newOpen, setNewOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newCategoryId, setNewCategoryId] = useState<string>("none")
  const [newColor, setNewColor] = useState("#64748b")
  const [newAliases, setNewAliases] = useState<string>("")

  // -- Edit Merchant Form --
  const [editOpen, setEditOpen] = useState(false)
  const [editingMerchant, setEditingMerchant] = useState<Merchant | null>(null)
  const [editName, setEditName] = useState("")
  const [editCategoryId, setEditCategoryId] = useState<string>("none")
  const [editColor, setEditColor] = useState("#64748b")
  const [newAliasLabel, setNewAliasLabel] = useState("")

  const loadData = async () => {
    setLoading(true)
    try {
      const [merchantsData, categoriesData, suggestionsData] = await Promise.all([
        api.get<Merchant[]>("/merchants"),
        api.get<Category[]>("/categories"),
        api.get<Suggestion[]>("/merchants/suggestions/unnormalized?min_count=5")
      ])
      setMerchants(merchantsData)
      setCategories(categoriesData)
      setSuggestions(suggestionsData)
    } catch (error) {
      toast.error("Erreur chargement données")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleAddMerchant = async () => {
    if (!newName) return
    const aliases = newAliases.split(",").map(s => s.trim()).filter(s => s.length > 0)
    try {
      await api.post("/merchants", {
        name: newName,
        category_id: newCategoryId === "none" ? null : parseInt(newCategoryId),
        color: newColor,
        aliases: aliases
      })
      toast.success("Marchand ajouté")
      setNewName("")
      setNewCategoryId("none")
      setNewColor("#64748b")
      setNewAliases("")
      setNewOpen(false)
      loadData()
    } catch (error) {
      toast.error("Erreur lors de l'ajout")
    }
  }

  const handleEditClick = (m: Merchant) => {
    setEditingMerchant(m)
    setEditName(m.name)
    setEditCategoryId(m.category_id ? String(m.category_id) : "none")
    setEditColor(m.color || "#64748b")
    setEditOpen(true)
  }

  const handleUpdateMerchant = async () => {
    if (!editingMerchant || !editName) return
    try {
      await api.put(`/merchants/${editingMerchant.id}`, {
        name: editName,
        category_id: editCategoryId === "none" ? null : parseInt(editCategoryId),
        color: editColor
      })
      toast.success("Marchand mis à jour")
      setEditOpen(false)
      loadData()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour")
    }
  }

  const handleDeleteMerchant = async (id: number) => {
    if (!confirm("Supprimer ce marchand canonique ?")) return
    try {
      await api.delete(`/merchants/${id}`)
      toast.success("Marchand supprimé")
      loadData()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  const handleAddAlias = async () => {
    if (!editingMerchant || !newAliasLabel) return
    try {
      await api.post(`/merchants/${editingMerchant.id}/aliases`, { label: newAliasLabel })
      setNewAliasLabel("")
      // Refresh current editing merchant aliases
      const updated = await api.get<Merchant>(`/merchants/${editingMerchant.id}`)
      setEditingMerchant(updated)
      // Also update in list to avoid extra reload
      setMerchants(merchants.map(m => m.id === updated.id ? updated : m))
      toast.success("Alias ajouté")
    } catch (error) {
      toast.error("L'alias existe déjà ou erreur")
    }
  }

  const handleRemoveAlias = async (aliasId: number) => {
    try {
      await api.delete(`/merchants/aliases/${aliasId}`)
      if (editingMerchant) {
        const updatedAliases = editingMerchant.aliases.filter(a => a.id !== aliasId)
        setEditingMerchant({ ...editingMerchant, aliases: updatedAliases })
        setMerchants(merchants.map(m => m.id === editingMerchant.id ? { ...m, aliases: updatedAliases } : m))
      }
      toast.success("Alias supprimé")
    } catch (error) {
      toast.error("Erreur suppression alias")
    }
  }

  const handleAutoNormalize = async () => {
    try {
      const result = await api.post<{ normalized_count: number }>("/merchants/auto-normalize", {})
      toast.success(`${result.normalized_count} transactions normalisées`)
      loadData()
    } catch (error) {
      toast.error("Erreur lors de la normalisation")
    }
  }

  const filteredMerchants = merchants.filter(m => 
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.aliases.some(a => a.label.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Normalisation des marchands</h2>
          <p className="text-slate-500 text-sm mt-1">Regroupez les variantes de libellés bancaires sous un marchand unique.</p>
        </div>
        
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleAutoNormalize} className="border-slate-200">
            <Wand2 className="h-4 w-4 mr-2" /> Auto-normaliser
          </Button>
          <Dialog open={newOpen} onOpenChange={setNewOpen}>
            <DialogTrigger asChild>
              <Button className="bg-slate-900 text-white hover:bg-slate-800 shadow-lg">
                <Plus className="h-4 w-4 mr-2" /> Nouveau marchand
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle className="text-2xl font-bold">Nouveau marchand canonique</DialogTitle>
                <DialogDescription>
                  Définissez un nom propre et ses variantes de libellés.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-6 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="new-m-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom Canonique</Label>
                  <Input 
                    id="new-m-name" 
                    placeholder="Ex: Amazon, Starbucks, Netflix..." 
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="bg-slate-50 border-slate-200"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Catégorie par défaut</Label>
                    <Select value={newCategoryId} onValueChange={setNewCategoryId}>
                      <SelectTrigger className="bg-slate-50 border-slate-200">
                        <SelectValue placeholder="Aucune" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Aucune</SelectItem>
                        {categories.map(c => (
                          <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
                    <Select value={newColor} onValueChange={setNewColor}>
                      <SelectTrigger className="bg-slate-50 border-slate-200">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {COLOR_OPTIONS.map(o => (
                          <SelectItem key={o.value} value={o.value}>
                            <div className="flex items-center gap-2">
                              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: o.value }} />
                              {o.name}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="new-aliases" className="text-xs font-bold uppercase tracking-wider text-slate-500">Variantes (séparées par des virgules)</Label>
                  <Input 
                    id="new-aliases" 
                    placeholder="Ex: AMZN Digital, AMAZON.FR, AMZN FR..." 
                    value={newAliases}
                    onChange={(e) => setNewAliases(e.target.value)}
                    className="bg-slate-50 border-slate-200"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="ghost" onClick={() => setNewOpen(false)}>Annuler</Button>
                <Button onClick={handleAddMerchant} className="bg-slate-900 text-white shadow-lg">Créer le marchand</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-3 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="Rechercher un marchand ou un libellé..." 
              className="pl-10 bg-white border-slate-200 h-12 rounded-xl"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {loading ? (
            <div className="text-center py-20 text-slate-400">Chargement...</div>
          ) : (
            <div className="grid gap-4">
              {filteredMerchants.map(m => (
                <Card key={m.id} className="group hover:border-slate-300 transition-all border-slate-100 shadow-sm overflow-hidden">
                  <CardContent className="p-0">
                    <div className="p-4 flex items-center justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div className="h-10 w-10 rounded-xl flex items-center justify-center text-white" style={{ backgroundColor: m.color || "#64748b" }}>
                          <ShoppingBag className="h-5 w-5" />
                        </div>
                        <div>
                          <p className="font-bold text-slate-900">{m.name}</p>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {m.aliases.length > 0 ? (
                              m.aliases.map(a => (
                                <Badge key={a.id} variant="secondary" className="bg-slate-50 text-slate-500 border-slate-200 text-[10px] font-medium h-5">
                                  {a.label}
                                </Badge>
                              ))
                            ) : (
                              <p className="text-[10px] text-slate-400 italic">Aucune variante définie</p>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button variant="ghost" size="sm" onClick={() => handleEditClick(m)} className="h-8 w-8 p-0 text-slate-500 hover:text-slate-900">
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteMerchant(m.id)} className="h-8 w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {filteredMerchants.length === 0 && (
                <div className="py-20 text-center bg-slate-50 rounded-3xl border-2 border-dashed border-slate-200">
                  <ShoppingBag className="h-10 w-10 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500 font-medium">Aucun marchand trouvé.</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-6">
          <Card className="border-amber-100 bg-amber-50/30">
            <CardHeader>
              <CardTitle className="text-sm font-bold flex items-center gap-2 text-amber-900">
                <AlertCircle className="h-4 w-4" /> Suggestions
              </CardTitle>
              <CardDescription className="text-xs">Libellés fréquents non normalisés.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {suggestions.map((s, i) => (
                <div key={i} className="flex items-center justify-between gap-2 p-2 bg-white rounded-lg border border-amber-100 shadow-sm">
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-slate-900 truncate">{s.label}</p>
                    <p className="text-[10px] text-slate-500">{s.count} occurrences</p>
                  </div>
                  <Button 
                    size="sm" 
                    variant="ghost" 
                    className="h-7 w-7 p-0 text-amber-600 hover:text-amber-700 hover:bg-amber-100"
                    onClick={() => {
                      setNewName(s.label)
                      setNewAliases(s.label)
                      setNewOpen(true)
                    }}
                  >
                    <PlusCircle className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              {suggestions.length === 0 && (
                <p className="text-xs text-slate-400 text-center py-4 italic">Tout est normalisé !</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">Modifier le marchand</DialogTitle>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-m-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom Canonique</Label>
              <Input 
                id="edit-m-name" 
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="bg-slate-50 border-slate-200"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Catégorie par défaut</Label>
                <Select value={editCategoryId} onValueChange={setEditCategoryId}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue placeholder="Aucune" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Aucune</SelectItem>
                    {categories.map(c => (
                      <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
                <Select value={editColor} onValueChange={setEditColor}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COLOR_OPTIONS.map(o => (
                      <SelectItem key={o.value} value={o.value}>
                        <div className="flex items-center gap-2">
                          <div className="h-3 w-3 rounded-full" style={{ backgroundColor: o.value }} />
                          {o.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Variantes de libellés</Label>
              <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 min-h-[60px]">
                {editingMerchant?.aliases.map(a => (
                  <Badge key={a.id} className="bg-white text-slate-700 border-slate-200 shadow-sm flex items-center gap-2 pr-1 h-7">
                    {a.label}
                    <button 
                      onClick={() => handleRemoveAlias(a.id)}
                      className="h-5 w-5 rounded-md hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-rose-500 transition-colors"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
                {editingMerchant?.aliases.length === 0 && (
                  <p className="text-xs text-slate-400 italic">Aucune variante.</p>
                )}
              </div>
              
              <div className="flex gap-2">
                <Input 
                  placeholder="Nouvelle variante..." 
                  className="bg-white h-9 text-sm"
                  value={newAliasLabel}
                  onChange={(e) => setNewAliasLabel(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddAlias()}
                />
                <Button size="sm" onClick={handleAddAlias} variant="secondary" className="h-9 px-3">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditOpen(false)}>Annuler</Button>
            <Button onClick={handleUpdateMerchant} className="bg-slate-900 text-white shadow-lg">Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
