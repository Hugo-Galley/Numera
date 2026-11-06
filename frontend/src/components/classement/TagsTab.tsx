import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { useState, useEffect } from "react"
import { Plus, Tag, Pencil, Trash2, Palette, Archive, ArchiveRestore } from "lucide-react"
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
import { useConfirm } from "@/providers/ConfirmProvider"
import { ErrorState } from "@/components/layout/ErrorState"

type TagType = {
  id: number
  name: string
  color: string | null
  archived?: boolean
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
  const { t } = useTranslation("classement")
  const confirm = useConfirm()
  const [tags, setTags] = useState<TagType[]>([])
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)

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
      setLoadFailed(false)
    } catch (error) {
      console.error("Failed to load tags", error)
      setLoadFailed(true)
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
      toast.success(t("tagsTab.tagAjoute"))
      setNewName("")
      setNewColor("#64748b")
      setNewOpen(false)
      loadTags()
    } catch (error) {
      toast.error(t("tagsTab.erreurLorsDeLAjout"))
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
      toast.success(t("tagsTab.tagMisAJour"))
      setEditOpen(false)
      loadTags()
    } catch (error) {
      toast.error(t("tagsTab.erreurLorsDeLaMise"))
    }
  }

  const handleToggleArchiveTag = async (tag: TagType) => {
    try {
      await api.patch(`/tags/${tag.id}`, { archived: !tag.archived })
      toast.success(tag.archived ? t("tagsTab.tagReactive") : t("tagsTab.tagArchiveMasqueDesSelecteurs"))
      loadTags()
    } catch (error) {
      toast.error(t("tagsTab.erreurLorsDeLArchivage"))
    }
  }

  const handleDeleteTag = async (tagId: number) => {
    if (!(await confirm(t("tagsTab.supprimerCeTagIlSera")))) return
    try {
      await api.delete(`/tags/${tagId}`)
      toast.success(t("tagsTab.tagSupprime"))
      loadTags()
    } catch (error) {
      toast.error(t("tagsTab.erreurLorsDeLaSuppression"))
    }
  }

  return (
    <div className="space-y-6 md:space-y-8 [&_input]:text-base md:[&_input]:text-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-slate-900">{t("tagsTab.gestionDesTags")}</h2>
          <p className="text-slate-500 text-sm mt-1">{t("tagsTab.utilisezLesTagsPourSuivre")}</p>
        </div>
        
        <Dialog open={newOpen} onOpenChange={setNewOpen}>
          <DialogTrigger asChild>
            <Button className="bg-slate-900 text-white hover:bg-slate-800 shadow-lg w-full sm:w-auto h-11 sm:h-10">
              <Plus className="h-4 w-4 mr-2" /> {t("tagsTab.nouveauTag")}
            </Button>
          </DialogTrigger>
          <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold">{t("tagsTab.nouveauTag")}</DialogTitle>
              <DialogDescription>
                {t("tagsTab.creezUnTagPersonnalisePour")}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-5 py-2 sm:gap-6 sm:py-4">
              <div className="grid gap-2">
                <Label htmlFor="new-tag-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">{t("tagsTab.nom")}</Label>
                <Input 
                  id="new-tag-name" 
                  placeholder={t("tagsTab.exVacancesTravaux")} 
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>

              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">{t("tagsTab.couleur")}</Label>
                <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 justify-center sm:justify-start">
                  {COLOR_OPTIONS.map((opt) => (
                    <button
                      key={opt.name}
                      type="button"
                      onClick={() => setNewColor(opt.value)}
                      className={`h-10 w-10 sm:h-8 sm:w-8 rounded-full border-4 transition-all ${newColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                      style={{ backgroundColor: opt.value }}
                      title={opt.name}
                    />
                  ))}
                </div>
              </div>

              <div className="theme-island flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
                <Badge 
                  className="px-3 py-1 font-bold shadow-sm border-none text-white"
                  style={{ backgroundColor: newColor }}
                >
                  <Tag className="h-3 w-3 mr-1.5" />
                  {newName || i18n.t("misc.tagPreview", { ns: "classement" })}
                </Badge>
              </div>
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setNewOpen(false)}>{t("tagsTab.annuler")}</Button>
              <Button onClick={handleAddTag} className="h-11 sm:h-10 bg-slate-900 text-white shadow-lg">{t("tagsTab.creerLeTag")}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <div className="text-center py-20 text-slate-400">{t("tagsTab.chargementDeVosTags")}</div>
      ) : loadFailed ? (
        <ErrorState message={t("tagsTab.impossibleDeChargerLesTags")} onRetry={() => { setLoading(true); loadTags() }} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[...tags].sort((a, b) => Number(!!a.archived) - Number(!!b.archived)).map((tag) => (
            <Card key={tag.id} className={`group hover:border-slate-300 transition-all shadow-sm border-slate-100 overflow-hidden ${tag.archived ? "opacity-60" : ""}`}>
              <CardContent className="p-0">
                <div className="p-3 pl-4 flex items-center justify-between gap-4 md:p-4">
                  <Badge 
                    className="px-3 py-1.5 font-bold shadow-sm border-none text-white truncate max-w-[200px] sm:max-w-[150px]"
                    style={{ backgroundColor: tag.color || "#64748b" }}
                  >
                    <Tag className="h-3.5 w-3.5 mr-2" />
                    {tag.name}
                  </Badge>
                  <div className="flex shrink-0 gap-1 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                    <Button aria-label={t("tagsTab.modifier")} variant="ghost" size="sm" onClick={() => handleEditClick(tag)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-500 hover:text-slate-900">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button aria-label={tag.archived ? t("tagsTab.reactiver") : t("tagsTab.archiver")} title={tag.archived ? t("tagsTab.reactiver") : t("tagsTab.archiver")} variant="ghost" size="sm" onClick={() => handleToggleArchiveTag(tag)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-500 hover:text-slate-900">
                      {tag.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
                    </Button>
                    <Button aria-label={t("tagsTab.supprimer")} variant="ghost" size="sm" onClick={() => handleDeleteTag(tag.id)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50">
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
              <p className="text-slate-500 font-medium">{t("tagsTab.aucunTagCreePourLe")}</p>
              <p className="text-slate-400 text-sm mt-1">{t("tagsTab.creezEnUnPourMieux")}</p>
            </div>
          )}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">{t("tagsTab.modifierLeTag")}</DialogTitle>
            <DialogDescription>{t("tagsTab.mettezAJourLesInformations")}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-2 sm:gap-6 sm:py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-tag-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">{t("tagsTab.nom")}</Label>
              <Input 
                id="edit-tag-name" 
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="bg-slate-50 border-slate-200"
              />
            </div>

            <div className="grid gap-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">{t("tagsTab.couleur")}</Label>
              <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.name}
                    type="button"
                    onClick={() => setEditColor(opt.value)}
                    className={`h-10 w-10 sm:h-8 sm:w-8 rounded-full border-4 transition-all ${editColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                    style={{ backgroundColor: opt.value }}
                    title={opt.name}
                  />
                ))}
              </div>
            </div>

            <div className="theme-island flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
              <Badge 
                className="px-3 py-1 font-bold shadow-sm border-none text-white"
                style={{ backgroundColor: editColor }}
              >
                <Tag className="h-3 w-3 mr-1.5" />
                {editName || i18n.t("misc.tagPreview", { ns: "classement" })}
              </Badge>
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setEditOpen(false)}>{t("tagsTab.annuler")}</Button>
            <Button onClick={handleUpdateTag} className="h-11 sm:h-10 bg-slate-900 text-white shadow-lg">{t("tagsTab.enregistrerLesModifications")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
