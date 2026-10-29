import { api } from "@/lib/api"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { Account, Category, ImportFlowProps, PreviewData } from "./types"

/** Comptes et catégories, fichier choisi, aperçu, correspondance des catégories et import. */
export function useImportState(p: { accountId: ImportFlowProps["accountId"]; onImported: ImportFlowProps["onImported"] }) {
  const { accountId, onImported } = p
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>(accountId ? String(accountId) : "")
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [createMissingCategories, setCreateMissingCategories] = useState(true)
  const [categoryMapping, setCategoryMapping] = useState<Record<string, string | number>>({})
  const [result, setResult] = useState<any | null>(null)

  const loadInitialData = async () => {
    try {
      const [accs, cats] = await Promise.all([
        api.get<Account[]>("/accounts"),
        api.get<Category[]>("/categories?include_archived=false"),
      ])
      
      if (accs && Array.isArray(accs)) {
        setAccounts(accs.filter((account) => account.active))
      }
      if (cats && Array.isArray(cats)) {
        setCategories(cats)
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
    e.target.value = "" // permet de re-sélectionner le même fichier après correction
    if (!selectedFile) return
    setFile(selectedFile)
    setPreview(null)
    setResult(null)
    setCategoryMapping({})

    const formData = new FormData()
    formData.append("file", selectedFile)

    setLoading(true)
    try {
      const data = await api.upload<any>("/import/preview", formData)
      setPreview(data)
      
      // Initialize mapping with default behavior (CREATE)
      const initialMapping: Record<string, string> = {}
      data.unknown_categories.forEach((cat: string) => {
        initialMapping[cat] = "CREATE"
      })
      setCategoryMapping(initialMapping)
    } catch (error: any) {
      toast.error(error?.message || "Erreur lors de l'analyse du fichier")
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
      const data = await api.upload<any>("/import/commit", formData)
      setResult(data)
      toast.success("Import terminé avec succès")
      if (data.imported > 0) onImported?.()
    } catch (error: any) {
      toast.error(error?.message || "Erreur lors de l'importation")
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

  return { accounts, setAccounts, categories, setCategories, selectedAccountId, setSelectedAccountId, file, setFile, preview, setPreview, loading, setLoading, importing, setImporting, createMissingCategories, setCreateMissingCategories, categoryMapping, setCategoryMapping, result, setResult, loadInitialData, handleFileChange, handleImport, handleMappingChange }
}
