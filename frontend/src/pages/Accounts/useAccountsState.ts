import { type LoanSummary } from "@/components/loans/types"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Account } from "./types"
import { getLoansByAccountById } from "@/lib/api/accounts"

/** État de la page : liste, formulaires, dialogues et liens ⌘K (?import=1, ?new=loan). */
export function useAccountsState() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | null>(null)
  
  const [newName, setNewName] = useState("")
  const [newType, setNewType] = useState<string>("courant")
  const [newCurrency, setNewCurrency] = useState<string>("EUR")
  const [newInstitution, setNewInstitution] = useState("")
  const [newLogo, setNewLogo] = useState<string | null>(null)
  const [newAssetClass, setNewAssetClass] = useState("")
  const [newSector, setNewSector] = useState("")
  const [newZone, setNewZone] = useState("")
  const [newValuationMode, setNewValuationMode] = useState<"positions" | "snapshot">("positions")
  const [newTaxWrapper, setNewTaxWrapper] = useState<string>("none")
  const [newOpenedAt, setNewOpenedAt] = useState("")
  const [newEurosPct, setNewEurosPct] = useState("")
  const [newInvestisPct, setNewInvestisPct] = useState("")
  const [sortField, setSortField] = useState<"name" | "type" | "currency" | "institution">("name")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")
  const [suggestions, setSuggestions] = useState<{
    asset_classes: string[],
    sectors: string[],
    geographic_zones: string[]
  }>({ asset_classes: [], sectors: [], geographic_zones: [] })

  const confirm = useConfirm()
  const [searchParams, setSearchParams] = useSearchParams()
  const [loanDialogOpen, setLoanDialogOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [editingLoan, setEditingLoan] = useState<LoanSummary | null>(null)

  // ⌘K « Importer un relevé » (et anciens liens /settings?tab=import) : /accounts?import=1
  useEffect(() => {
    if (searchParams.get("import") !== "1") return
    setImportOpen(true)
    searchParams.delete("import")
    setSearchParams(searchParams, { replace: true })
  }, [searchParams, setSearchParams])

  // ⌘K « Ajouter un crédit » : /accounts?new=loan
  useEffect(() => {
    if (searchParams.get("new") !== "loan") return
    setEditingLoan(null)
    setLoanDialogOpen(true)
    searchParams.delete("new")
    setSearchParams(searchParams, { replace: true })
  }, [searchParams, setSearchParams])

  // Un compte crédit se modifie avec son prêt (le formulaire de compte refuserait le type `credit`)
  const openEdit = async (account: Account) => {
    if (account.type !== "credit") {
      setEditingAccount(account)
      setIsEditDialogOpen(true)
      return
    }
    try {
      setEditingLoan(await getLoansByAccountById<LoanSummary>(account.id))
      setLoanDialogOpen(true)
    } catch (error) {
      toast.error("Impossible de charger ce crédit")
    }
  }
  const [archivedAccounts, setArchivedAccounts] = useState<Account[]>([])
  const [showArchived, setShowArchived] = useState(false)

  return { accounts, setAccounts, loading, setLoading, isDialogOpen, setIsDialogOpen, isEditDialogOpen, setIsEditDialogOpen, editingAccount, setEditingAccount, newName, setNewName, newType, setNewType, newCurrency, setNewCurrency, newInstitution, setNewInstitution, newLogo, setNewLogo, newAssetClass, setNewAssetClass, newSector, setNewSector, newZone, setNewZone, newValuationMode, setNewValuationMode, newTaxWrapper, setNewTaxWrapper, newOpenedAt, setNewOpenedAt, newEurosPct, setNewEurosPct, newInvestisPct, setNewInvestisPct, sortField, setSortField, sortOrder, setSortOrder, suggestions, setSuggestions, confirm, searchParams, setSearchParams, loanDialogOpen, setLoanDialogOpen, importOpen, setImportOpen, editingLoan, setEditingLoan, openEdit, archivedAccounts, setArchivedAccounts, showArchived, setShowArchived }
}
