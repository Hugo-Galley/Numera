import { api } from "@/lib/api"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useEffect, useState } from "react"
import { Category, Merchant, Suggestion } from "./types"

/** Chargement des marchands, création, modification, alias et normalisation automatique. */
export function useMerchantsData() {
  const confirm = useConfirm()
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
        api.get<Category[]>("/categories?include_archived=false"),
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
    if (!(await confirm("Supprimer ce marchand canonique ?"))) return
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

  return { confirm, merchants, setMerchants, categories, setCategories, suggestions, setSuggestions, loading, setLoading, search, setSearch, newOpen, setNewOpen, newName, setNewName, newCategoryId, setNewCategoryId, newColor, setNewColor, newAliases, setNewAliases, editOpen, setEditOpen, editingMerchant, setEditingMerchant, editName, setEditName, editCategoryId, setEditCategoryId, editColor, setEditColor, newAliasLabel, setNewAliasLabel, loadData, handleAddMerchant, handleEditClick, handleUpdateMerchant, handleDeleteMerchant, handleAddAlias, handleRemoveAlias, handleAutoNormalize, filteredMerchants }
}
