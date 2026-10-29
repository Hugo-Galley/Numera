import { api } from "@/lib/api"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useEffect, useState } from "react"
import { useSubmit } from "@/hooks/useSubmit"
import { Category } from "./types"

/** Chargement des catégories, création, modification, archivage et suppression. */
export function useCategoriesData() {
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

  return { confirm, categories, setCategories, loading, setLoading, newOpen, setNewOpen, newCatName, setNewCatName, newCatType, setNewCatType, newCatIcon, setNewCatIcon, newCatColor, setNewCatColor, newCatGroup, setNewCatGroup, newMonthlyLimit, setNewMonthlyLimit, newAnnualLimit, setNewAnnualLimit, editOpen, setEditOpen, editingCat, setEditingCat, editCatName, setEditCatName, editCatType, setEditCatType, editCatIcon, setEditCatIcon, editCatColor, setEditCatColor, editCatGroup, setEditCatGroup, editMonthlyLimit, setEditMonthlyLimit, editAnnualLimit, setEditAnnualLimit, loadCategories, handleAddCategory, handleAddCategoryBusy, handleEditClick, handleUpdateCategory, handleUpdateCategoryBusy, showArchivedCats, setShowArchivedCats, handleToggleArchiveCategory, handleDeleteCategory }
}
