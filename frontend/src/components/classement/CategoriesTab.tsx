import { useEffect, useState } from "react"
import { Archive, ArchiveRestore, Pencil, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { IconComponent, ICON_OPTIONS } from "@/components/dashboard/IconComponent"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useSubmit } from "@/hooks/useSubmit"
import { api } from "@/lib/api"
import { categoryTypeLabel } from "@/lib/labels"
import { useConfirm } from "@/providers/ConfirmProvider"

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

type Category = {
  id: number
  name: string
  type: "depense" | "revenu" | "neutre"
  icon?: string
  color?: string
  group?: string | null
  monthly_limit?: number | null
  annual_limit?: number | null
  archived?: boolean
}

export function CategoriesTab() {
  const confirm = useConfirm()
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)

  // -- New Category Form --
  const [newOpen, setNewOpen] = useState(false)
  const [newCatName, setNewCatName] = useState("")
  const [newCatType, setNewCatType] = useState<"depense" | "revenu" | "neutre">("depense")
  const [newCatIcon, setNewCatIcon] = useState("Tag")
  const [newCatColor, setNewCatColor] = useState("#64748b")
  const [newCatGroup, setNewCatGroup] = useState("")
  const [newMonthlyLimit, setNewMonthlyLimit] = useState("")
  const [newAnnualLimit, setNewAnnualLimit] = useState("")

  // -- Edit Category Form --
  const [editOpen, setEditOpen] = useState(false)
  const [editingCat, setEditingCat] = useState<Category | null>(null)
  const [editCatName, setEditCatName] = useState("")
  const [editCatType, setEditCatType] = useState<"depense" | "revenu" | "neutre">("depense")
  const [editCatIcon, setEditCatIcon] = useState("Tag")
  const [editCatColor, setEditCatColor] = useState("#64748b")
  const [editCatGroup, setEditCatGroup] = useState("")
  const [editMonthlyLimit, setEditMonthlyLimit] = useState("")
  const [editAnnualLimit, setEditAnnualLimit] = useState("")

  const loadCategories = async () => {
    try {
      const data = await api.get<Category[]>("/categories")
      setCategories(data)
    } catch (error) {
      toast.error("Erreur chargement catégories")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCategories()
  }, [])

  const [handleAddCategory, handleAddCategoryBusy] = useSubmit(async () => {
    if (!newCatName) return
    try {
      await api.post("/categories", {
        name: newCatName,
        type: newCatType,
        icon: newCatIcon,
        color: newCatColor,
        group: newCatGroup || null,
        monthly_limit: newMonthlyLimit ? parseFloat(newMonthlyLimit) : null,
        annual_limit: newAnnualLimit ? parseFloat(newAnnualLimit) : null,
      })
      toast.success("Catégorie ajoutée")
      setNewCatName("")
      setNewCatType("depense")
      setNewCatIcon("Tag")
      setNewCatColor("#64748b")
      setNewCatGroup("")
      setNewMonthlyLimit("")
      setNewAnnualLimit("")
      setNewOpen(false)
      loadCategories()
    } catch (error) {
      toast.error("Erreur lors de l'ajout")
    }
  })

  const handleEditClick = (cat: Category) => {
    setEditingCat(cat)
    setEditCatName(cat.name)
    setEditCatType(cat.type)
    setEditCatIcon(cat.icon || "Tag")
    setEditCatColor(cat.color || "#64748b")
    setEditCatGroup(cat.group || "")
    setEditMonthlyLimit(cat.monthly_limit != null ? String(cat.monthly_limit) : "")
    setEditAnnualLimit(cat.annual_limit != null ? String(cat.annual_limit) : "")
    setEditOpen(true)
  }

  const [handleUpdateCategory, handleUpdateCategoryBusy] = useSubmit(async () => {
    if (!editingCat || !editCatName) return
    try {
      await api.patch(`/categories/${editingCat.id}`, {
        name: editCatName,
        type: editCatType,
        icon: editCatIcon,
        color: editCatColor,
        group: editCatGroup || null,
        monthly_limit: editMonthlyLimit ? parseFloat(editMonthlyLimit) : null,
        annual_limit: editAnnualLimit ? parseFloat(editAnnualLimit) : null,
      })
      toast.success("Catégorie mise à jour")
      setEditOpen(false)
      loadCategories()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour")
    }
  })

  const [showArchivedCats, setShowArchivedCats] = useState(false)

  const handleToggleArchiveCategory = async (cat: Category) => {
    try {
      await api.patch(`/categories/${cat.id}`, { archived: !cat.archived })
      toast.success(cat.archived ? "Catégorie réactivée" : "Catégorie archivée : masquée des sélecteurs, historique conservé")
      loadCategories()
    } catch (error) {
      toast.error("Erreur lors de l'archivage")
    }
  }

  const handleDeleteCategory = async (categoryId: number) => {
    if (!(await confirm("Supprimer cette catégorie ? Les transactions associées n'auront plus de catégorie."))) return
    try {
      await api.delete(`/categories/${categoryId}`)
      toast.success("Catégorie supprimée")
      loadCategories()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  return (
    <div className="space-y-8 [&_input]:text-base md:[&_input]:text-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h2 className="text-xl md:text-2xl font-bold text-slate-900">Gestion des catégories</h2>
        
        <Dialog open={newOpen} onOpenChange={setNewOpen}>
          <DialogTrigger asChild>
            <Button className="bg-slate-900 text-white hover:bg-slate-800 shadow-lg w-full sm:w-auto h-11 sm:h-10">
              <Plus className="h-4 w-4 mr-2" /> Nouvelle catégorie
            </Button>
          </DialogTrigger>
          <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold">Nouvelle catégorie</DialogTitle>
              <DialogDescription>
                Créez une catégorie personnalisée avec son icône et sa couleur.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-5 py-2 sm:gap-6 sm:py-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="new-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom</Label>
                  <Input 
                    id="new-name" 
                    placeholder="Ex: Streaming..." 
                    value={newCatName}
                    onChange={(e) => setNewCatName(e.target.value)}
                    className="bg-slate-50 border-slate-200"
                  />
                </div>
                <div className="grid gap-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Nature</Label>
                  <Select value={newCatType} onValueChange={(v: any) => setNewCatType(v)}>
                    <SelectTrigger className="bg-slate-50 border-slate-200">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="depense">Dépense (-)</SelectItem>
                      <SelectItem value="revenu">Revenu (+)</SelectItem>
                      <SelectItem value="neutre">Neutre</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="new-group" className="text-xs font-bold uppercase tracking-wider text-slate-500">Groupe (pour Sankey)</Label>
                <Input 
                  id="new-group" 
                  placeholder="Ex: Vie courante, Loisirs..." 
                  value={newCatGroup}
                  onChange={(e) => setNewCatGroup(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>

              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Icône</Label>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="grid grid-cols-6 sm:grid-cols-10 gap-1 sm:gap-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                    {ICON_OPTIONS.map((iconName) => (
                      <button
                        key={iconName}
                        type="button"
                        aria-label={`Icône ${iconName}`}
                        aria-pressed={newCatIcon === iconName}
                        onClick={() => setNewCatIcon(iconName)}
                        className={`p-3 sm:p-2 rounded-lg flex items-center justify-center transition-all ${newCatIcon === iconName ? 'bg-slate-900 text-white' : 'hover:bg-slate-200 text-slate-500'}`}
                      >
                        <IconComponent name={iconName} className="h-4 w-4" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
                <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 justify-center sm:justify-start">
                  {COLOR_OPTIONS.map((opt) => (
                    <button
                      key={opt.name}
                      type="button"
                      onClick={() => setNewCatColor(opt.value)}
                      className={`h-10 w-10 sm:h-8 sm:w-8 rounded-full border-4 transition-all ${newCatColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                      style={{ backgroundColor: opt.value }}
                      title={opt.name}
                    />
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="new-monthly-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite mensuelle (€)</Label>
                  <Input
                    id="new-monthly-limit"
                    type="number" inputMode="decimal"
                    min="0"
                    placeholder="Ex: 200"
                    value={newMonthlyLimit}
                    onChange={(e) => setNewMonthlyLimit(e.target.value)}
                    className="bg-slate-50 border-slate-200"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="new-annual-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite annuelle (€)</Label>
                  <Input
                    id="new-annual-limit"
                    type="number" inputMode="decimal"
                    min="0"
                    placeholder="Ex: 2400"
                    value={newAnnualLimit}
                    onChange={(e) => setNewAnnualLimit(e.target.value)}
                    className="bg-slate-50 border-slate-200"
                  />
                </div>
              </div>

              <div className="theme-island flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
                <div className="h-10 w-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: newCatColor }}>
                  <IconComponent name={newCatIcon} className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm font-bold">{newCatName || "Nom de la catégorie"}</p>
                  <p className="text-[10px] uppercase font-black opacity-50 tracking-widest">{newCatType}</p>
                </div>
              </div>
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setNewOpen(false)}>Annuler</Button>
              <Button onClick={() => handleAddCategory()} disabled={handleAddCategoryBusy} className="h-11 bg-slate-900 text-white shadow-lg sm:h-10">Créer la catégorie</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
         <div className="text-center py-20 text-slate-400">Chargement de vos catégories...</div>
      ) : (
        <>
        <div className="grid gap-3 md:gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {categories.filter((cat) => showArchivedCats || !cat.archived).map((cat) => (
            <Card key={cat.id} className={`group hover:border-slate-300 transition-all shadow-sm border-slate-100 overflow-hidden ${cat.archived ? "opacity-60" : ""}`}>
              <CardContent className="p-0">
                <div className="p-3 pl-4 md:p-4 flex items-center gap-3 md:gap-4">
                  <div className="h-12 w-12 shrink-0 rounded-2xl flex items-center justify-center shadow-sm" style={{ backgroundColor: cat.color || "#64748b" }}>
                    <IconComponent name={cat.icon} className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-slate-900 truncate">{cat.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className={`
                        text-[9px] uppercase font-black border-none px-0
                        ${cat.type === 'depense' ? 'text-rose-500' : ''}
                        ${cat.type === 'revenu' ? 'text-emerald-500' : ''}
                        ${cat.type === 'neutre' ? 'text-slate-400' : ''}
                      `}>
                        {categoryTypeLabel(cat.type)}
                      </Badge>
                      {cat.group && (
                        <Badge variant="secondary" className="text-[9px] h-4 px-1 bg-slate-100 text-slate-500 border-none font-bold">
                          {cat.group}
                        </Badge>
                      )}
                    </div>
                    {cat.monthly_limit != null && (
                      <p className="text-[10px] text-amber-600 font-semibold mt-0.5">{cat.monthly_limit}€/mois</p>
                    )}
                    {cat.archived && <p className="text-[10px] text-slate-400 font-semibold mt-0.5">Archivée</p>}
                  </div>
                  <div className="flex shrink-0 gap-0 md:hidden">
                    <Button variant="ghost" size="sm" onClick={() => handleEditClick(cat)} aria-label="Modifier" className="h-10 w-10 p-0 text-slate-500">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleToggleArchiveCategory(cat)} aria-label={cat.archived ? "Réactiver" : "Archiver"} title={cat.archived ? "Réactiver" : "Archiver"} className="h-10 w-10 p-0 text-slate-500">
                      {cat.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteCategory(cat.id)} aria-label="Supprimer" className="h-10 w-10 p-0 text-rose-500 hover:bg-rose-50">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="hidden md:flex px-4 py-3 bg-slate-50/50 border-t justify-between items-center md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                  <p className="text-[10px] text-slate-400 font-medium">ID: #{cat.id}</p>
                  <div className="flex gap-1">
                    <Button aria-label="Modifier" variant="ghost" size="sm" onClick={() => handleEditClick(cat)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-500 hover:text-slate-900">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button aria-label={cat.archived ? "Réactiver" : "Archiver"} title={cat.archived ? "Réactiver" : "Archiver"} variant="ghost" size="sm" onClick={() => handleToggleArchiveCategory(cat)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-500 hover:text-slate-900">
                      {cat.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
                    </Button>
                    <Button aria-label="Supprimer" variant="ghost" size="sm" onClick={() => handleDeleteCategory(cat.id)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        {categories.some((cat) => cat.archived) && (
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={() => setShowArchivedCats((v) => !v)}>
            <Archive className="mr-2 h-4 w-4" />
            {showArchivedCats ? "Masquer les catégories archivées" : `Afficher les catégories archivées (${categories.filter((cat) => cat.archived).length})`}
          </Button>
        )}
        </>
      )}

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">Modifier la catégorie</DialogTitle>
            <DialogDescription>Mettez à jour les informations de votre catégorie.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-2 sm:gap-6 sm:py-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom</Label>
                <Input 
                  id="edit-name" 
                  value={editCatName}
                  onChange={(e) => setEditCatName(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>
              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Nature</Label>
                <Select value={editCatType} onValueChange={(v: any) => setEditCatType(v)}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="depense">Dépense (-)</SelectItem>
                    <SelectItem value="revenu">Revenu (+)</SelectItem>
                    <SelectItem value="neutre">Neutre</SelectItem>
                  </SelectContent>
                  </Select>
                  </div>
                  </div>

                  <div className="grid gap-2">
                  <Label htmlFor="edit-group" className="text-xs font-bold uppercase tracking-wider text-slate-500">Groupe (pour Sankey)</Label>
                  <Input 
                  id="edit-group" 
                  placeholder="Ex: Vie courante, Loisirs..." 
                  value={editCatGroup}
                  onChange={(e) => setEditCatGroup(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                  />
                  </div>

                  <div className="grid gap-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Icône</Label>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="grid grid-cols-6 sm:grid-cols-10 gap-1 sm:gap-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                  {ICON_OPTIONS.map((iconName) => (
                    <button
                      key={iconName}
                      type="button"
                      aria-label={`Icône ${iconName}`}
                      aria-pressed={editCatIcon === iconName}
                      onClick={() => setEditCatIcon(iconName)}
                      className={`p-3 sm:p-2 rounded-lg flex items-center justify-center transition-all ${editCatIcon === iconName ? 'bg-slate-900 text-white' : 'hover:bg-slate-200 text-slate-500'}`}
                    >
                      <IconComponent name={iconName} className="h-4 w-4" />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid gap-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
              <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.name}
                    type="button"
                    onClick={() => setEditCatColor(opt.value)}
                    className={`h-10 w-10 sm:h-8 sm:w-8 rounded-full border-4 transition-all ${editCatColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                    style={{ backgroundColor: opt.value }}
                    title={opt.name}
                  />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-monthly-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite mensuelle (€)</Label>
                <Input
                  id="edit-monthly-limit"
                  type="number" inputMode="decimal"
                  min="0"
                  placeholder="Ex: 200"
                  value={editMonthlyLimit}
                  onChange={(e) => setEditMonthlyLimit(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-annual-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite annuelle (€)</Label>
                <Input
                  id="edit-annual-limit"
                  type="number" inputMode="decimal"
                  min="0"
                  placeholder="Ex: 2400"
                  value={editAnnualLimit}
                  onChange={(e) => setEditAnnualLimit(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>
            </div>

            <div className="theme-island flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
              <div className="h-10 w-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: editCatColor }}>
                <IconComponent name={editCatIcon} className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm font-bold">{editCatName || "Nom de la catégorie"}</p>
                <p className="text-[10px] uppercase font-black opacity-50 tracking-widest">{editCatType}</p>
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setEditOpen(false)}>Annuler</Button>
            <Button onClick={() => handleUpdateCategory()} disabled={handleUpdateCategoryBusy} className="h-11 bg-slate-900 text-white shadow-lg sm:h-10">Enregistrer les modifications</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
