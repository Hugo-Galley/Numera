import i18n from "i18next"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useEffect, useState } from "react"
import { Category, Merchant, Suggestion } from "./types"
import { deleteMerchantsAliasesById, deleteMerchantsById, getCategories, getMerchants, getMerchantsById, getMerchantsSuggestionsUnnormalized, postMerchants, postMerchantsAliases, postMerchantsAutoNormalize, putMerchantsById } from "@/lib/api/classement"

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
        getMerchants<Merchant[]>(),
        getCategories<Category[]>("?include_archived=false"),
        getMerchantsSuggestionsUnnormalized<Suggestion[]>("?min_count=5")
      ])
      setMerchants(merchantsData)
      setCategories(categoriesData)
      setSuggestions(suggestionsData)
    } catch (error) {
      toast.error(i18n.t("useMerchantsData.erreurChargementDonnees", { ns: "classement" }))
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
      await postMerchants({
        name: newName,
        category_id: newCategoryId === "none" ? null : parseInt(newCategoryId),
        color: newColor,
        aliases: aliases
      })
      toast.success(i18n.t("useMerchantsData.marchandAjoute", { ns: "classement" }))
      setNewName("")
      setNewCategoryId("none")
      setNewColor("#64748b")
      setNewAliases("")
      setNewOpen(false)
      loadData()
    } catch (error) {
      toast.error(i18n.t("useMerchantsData.erreurLorsDeLAjout", { ns: "classement" }))
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
      await putMerchantsById(editingMerchant.id, {
        name: editName,
        category_id: editCategoryId === "none" ? null : parseInt(editCategoryId),
        color: editColor
      })
      toast.success(i18n.t("useMerchantsData.marchandMisAJour", { ns: "classement" }))
      setEditOpen(false)
      loadData()
    } catch (error) {
      toast.error(i18n.t("useMerchantsData.erreurLorsDeLaMise", { ns: "classement" }))
    }
  }

  const handleDeleteMerchant = async (id: number) => {
    if (!(await confirm(i18n.t("useMerchantsData.supprimerCeMarchandCanonique", { ns: "classement" })))) return
    try {
      await deleteMerchantsById(id)
      toast.success(i18n.t("useMerchantsData.marchandSupprime", { ns: "classement" }))
      loadData()
    } catch (error) {
      toast.error(i18n.t("useMerchantsData.erreurLorsDeLaSuppression", { ns: "classement" }))
    }
  }

  const handleAddAlias = async () => {
    if (!editingMerchant || !newAliasLabel) return
    try {
      await postMerchantsAliases(editingMerchant.id, { label: newAliasLabel })
      setNewAliasLabel("")
      // Refresh current editing merchant aliases
      const updated = await getMerchantsById<Merchant>(editingMerchant.id)
      setEditingMerchant(updated)
      // Also update in list to avoid extra reload
      setMerchants(merchants.map(m => m.id === updated.id ? updated : m))
      toast.success(i18n.t("useMerchantsData.aliasAjoute", { ns: "classement" }))
    } catch (error) {
      toast.error(i18n.t("useMerchantsData.lAliasExisteDejaOu", { ns: "classement" }))
    }
  }

  const handleRemoveAlias = async (aliasId: number) => {
    try {
      await deleteMerchantsAliasesById(aliasId)
      if (editingMerchant) {
        const updatedAliases = editingMerchant.aliases.filter(a => a.id !== aliasId)
        setEditingMerchant({ ...editingMerchant, aliases: updatedAliases })
        setMerchants(merchants.map(m => m.id === editingMerchant.id ? { ...m, aliases: updatedAliases } : m))
      }
      toast.success(i18n.t("useMerchantsData.aliasSupprime", { ns: "classement" }))
    } catch (error) {
      toast.error(i18n.t("useMerchantsData.erreurSuppressionAlias", { ns: "classement" }))
    }
  }

  const handleAutoNormalize = async () => {
    try {
      const result = await postMerchantsAutoNormalize<{ normalized_count: number }>({})
      toast.success(i18n.t("misc.normalized", { ns: "classement", count: result.normalized_count }))
      loadData()
    } catch (error) {
      toast.error(i18n.t("useMerchantsData.erreurLorsDeLaNormalisation", { ns: "classement" }))
    }
  }

  const filteredMerchants = merchants.filter(m => 
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.aliases.some(a => a.label.toLowerCase().includes(search.toLowerCase()))
  )

  return { confirm, merchants, setMerchants, categories, setCategories, suggestions, setSuggestions, loading, setLoading, search, setSearch, newOpen, setNewOpen, newName, setNewName, newCategoryId, setNewCategoryId, newColor, setNewColor, newAliases, setNewAliases, editOpen, setEditOpen, editingMerchant, setEditingMerchant, editName, setEditName, editCategoryId, setEditCategoryId, editColor, setEditColor, newAliasLabel, setNewAliasLabel, loadData, handleAddMerchant, handleEditClick, handleUpdateMerchant, handleDeleteMerchant, handleAddAlias, handleRemoveAlias, handleAutoNormalize, filteredMerchants }
}
