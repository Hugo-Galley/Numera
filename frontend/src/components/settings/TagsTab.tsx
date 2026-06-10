import { useState, useEffect } from "react"
import { Plus, Tag, Pencil, Trash2, Palette } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
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

type TagType = {
  id: number
  name: string
  color: string | null
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

export function TagsTab() {
  const [tags, setTags] = useState<TagType[]>([])
  const [loading, setLoading] = useState(true)

  // -- New Tag Form --
  const [newOpen, setNewOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newColor, setNewColor] = useState("#64748b")

  // -- Edit Tag Form --
  const [editOpen, setEditOpen] = useState(false)
  const [editingTag, setEditingTag] = useState<TagType | null>(null)
  const [editName, setEditName] = useState("")
  const [editColor, setEditColor] = useState("#64748b")

  const loadTags = async () => {
    try {
      const data = await api.get<TagType[]>("/tags")
      setTags(data)
    } catch (error) {
      toast.error("Erreur chargement tags")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTags()
  }, [])

  const handleAddTag = async () => {
    if (!newName) return
    try {
      await api.post("/tags", {
        name: newName,
        color: newColor,
      })
      toast.success("Tag ajouté")
      setNewName("")
      setNewColor("#64748b")
      setNewOpen(false)
      loadTags()
    } catch (error) {
      toast.error("Erreur lors de l'ajout")
    }
  }

  const handleEditClick = (tag: TagType) => {
    setEditingTag(tag)
    setEditName(tag.name)
    setEditColor(tag.color || "#64748b")
    setEditOpen(true)
  }

  const handleUpdateTag = async () => {
    if (!editingTag || !editName) return
    try {
      await api.patch(`/tags/${editingTag.id}`, {
        name: editName,
        color: editColor,
      })
      toast.success("Tag mis à jour")
      setEditOpen(false)
      loadTags()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour")
    }
  }

  const handleDeleteTag = async (tagId: number) => {
    if (!confirm("Supprimer ce tag ? Il sera retiré de toutes les transactions.")) return
    try {
      await api.delete(`/tags/${tagId}`)
      toast.success("Tag supprimé")
      loadTags()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Gestion des tags</h2>
          <p className="text-slate-500 text-sm mt-1">Utilisez les tags pour suivre des projets ou contextes transverses.</p>
        </div>
        
        <Dialog open={newOpen} onOpenChange={setNewOpen}>
          <DialogTrigger asChild>
            <Button className="bg-slate-900 text-white hover:bg-slate-800 shadow-lg w-full sm:w-auto">
              <Plus className="h-4 w-4 mr-2" /> Nouveau tag
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold">Nouveau tag</DialogTitle>
              <DialogDescription>
                Créez un tag personnalisé pour vos transactions.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-6 py-4">
              <div className="grid gap-2">
                <Label htmlFor="new-tag-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom</Label>
                <Input 
                  id="new-tag-name" 
                  placeholder="Ex: Vacances, Travaux..." 
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>

              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
                <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 justify-center sm:justify-start">
                  {COLOR_OPTIONS.map((opt) => (
                    <button
                      key={opt.name}
                      type="button"
                      onClick={() => setNewColor(opt.value)}
                      className={`h-8 w-8 rounded-full border-4 transition-all ${newColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                      style={{ backgroundColor: opt.value }}
                      title={opt.name}
                    />
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
                <Badge 
                  className="px-3 py-1 font-bold shadow-sm border-none"
                  style={{ backgroundColor: newColor }}
                >
                  <Tag className="h-3 w-3 mr-1.5" />
                  {newName || "Aperçu du tag"}
                </Badge>
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setNewOpen(false)}>Annuler</Button>
              <Button onClick={handleAddTag} className="bg-slate-900 text-white shadow-lg">Créer le tag</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <div className="text-center py-20 text-slate-400">Chargement de vos tags...</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {tags.map((tag) => (
            <Card key={tag.id} className="group hover:border-slate-300 transition-all shadow-sm border-slate-100 overflow-hidden">
              <CardContent className="p-0">
                <div className="p-4 flex items-center justify-between gap-4">
                  <Badge 
                    className="px-3 py-1.5 font-bold shadow-sm border-none truncate max-w-[150px]"
                    style={{ backgroundColor: tag.color || "#64748b" }}
                  >
                    <Tag className="h-3.5 w-3.5 mr-2" />
                    {tag.name}
                  </Badge>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="sm" onClick={() => handleEditClick(tag)} className="h-8 w-8 p-0 text-slate-500 hover:text-slate-900">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteTag(tag.id)} className="h-8 w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          {tags.length === 0 && (
            <div className="col-span-full py-20 text-center bg-slate-50 rounded-3xl border-2 border-dashed border-slate-200">
              <Tag className="h-10 w-10 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500 font-medium">Aucun tag créé pour le moment.</p>
              <p className="text-slate-400 text-sm mt-1">Créez-en un pour mieux organiser vos dépenses.</p>
            </div>
          )}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">Modifier le tag</DialogTitle>
            <DialogDescription>Mettez à jour les informations de votre tag.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-tag-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom</Label>
              <Input 
                id="edit-tag-name" 
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="bg-slate-50 border-slate-200"
              />
            </div>

            <div className="grid gap-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
              <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.name}
                    type="button"
                    onClick={() => setEditColor(opt.value)}
                    className={`h-8 w-8 rounded-full border-4 transition-all ${editColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                    style={{ backgroundColor: opt.value }}
                    title={opt.name}
                  />
                ))}
              </div>
            </div>

            <div className="flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
              <Badge 
                className="px-3 py-1 font-bold shadow-sm border-none"
                style={{ backgroundColor: editColor }}
              >
                <Tag className="h-3 w-3 mr-1.5" />
                {editName || "Aperçu du tag"}
              </Badge>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditOpen(false)}>Annuler</Button>
            <Button onClick={handleUpdateTag} className="bg-slate-900 text-white shadow-lg">Enregistrer les modifications</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
