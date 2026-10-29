import { type AccountLite } from "@/types/transfers"
import { PortfolioHolding } from "@/types/diversity"
import { endOfMonth, endOfYear, format, startOfMonth, startOfYear, subMonths } from "date-fns"
import { formatCurrency as formatCurrencyShared } from "@/lib/utils"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useMemo, useState } from "react"
import { useParams } from "react-router-dom"
import { Account, Category, TagType, Transaction } from "./types"

/** État de la page : compte, liste, filtres, tris et sélection. */
export function useAccountDetailState() {
  const confirm = useConfirm()
  const { id } = useParams<{ id: string }>()
  
  // -- Data State --
  const [account, setAccount] = useState<Account | null>(null)
  const [transferTx, setTransferTx] = useState<Transaction | null>(null)
  const [reconcileOpen, setReconcileOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [reimbursementTx, setReimbursementTx] = useState<Transaction | null>(null)
  const [splitTx, setSplitTx] = useState<Transaction | null>(null)
  const [allAccounts, setAllAccounts] = useState<AccountLite[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [hasMoreTx, setHasMoreTx] = useState(false)
  const [loadingMoreTx, setLoadingMoreTx] = useState(false)
  const [flowSummary, setFlowSummary] = useState<{
    monthly_net_flow: number
    prev_monthly_net_flow: number
    monthly_variation: number | null
    avg_expense: number
  } | null>(null)
  const [knownMerchants, setKnownMerchants] = useState<string[]>([])
  const [timeseries, setTimeseries] = useState<any>(null)
  const [investmentData, setInvestmentData] = useState<any>(null)
  const [perfHistory, setPerfHistory] = useState<any[]>([])
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [availableTags, setAvailableTags] = useState<TagType[]>([])
  const [tagTotals, setTagTotals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [dateStart, setDateStart] = useState("")
  const [dateEnd, setDateEnd] = useState("")
  const [sortField, setSortField] = useState<"date" | "merchant" | "amount" | "category" | "type" | "running_balance">("date")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [invSortField, setInvSortField] = useState<"date" | "type" | "amount">("date")
  const [invSortOrder, setInvSortOrder] = useState<"asc" | "desc">("desc")
  const [snapSortField, setSnapSortField] = useState<"date" | "current_value">("date")
  const [snapSortOrder, setSnapSortOrder] = useState<"asc" | "desc">("desc")

  const [filterType, setFilterType] = useState<string>("all")
  const [filterCategory, setFilterCategory] = useState<string>("all")
  const [filterMerchant, setFilterMerchant] = useState<string>("all")
  const [filterTags, setFilterTags] = useState<number[]>([])

  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [isBulkEditDialogOpen, setIsBulkEditDialogOpen] = useState(false)
  const [bulkCategory, setBulkCategory] = useState<string>("keep")
  const [bulkRecurring, setBulkRecurring] = useState<string>("keep")
  const [bulkTagIds, setBulkTagIds] = useState<number[]>([])
  const [bulkTagAction, setBulkTagAction] = useState<"keep" | "replace">("keep")

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortOrder("desc")
    }
  }

  const handleInvSort = (field: typeof invSortField) => {
    if (invSortField === field) {
      setInvSortOrder(invSortOrder === "asc" ? "desc" : "asc")
    } else {
      setInvSortField(field)
      setInvSortOrder("desc")
    }
  }

  const sortedInvestmentTransactions = useMemo(() => {
    return [...(investmentData?.transactions || [])].sort((a, b) => {
      let comparison = 0
      switch (invSortField) {
        case "date":
          comparison = new Date(a.date).getTime() - new Date(b.date).getTime()
          break
        case "type":
          comparison = a.type.localeCompare(b.type)
          break
        case "amount":
          comparison = a.amount - b.amount
          break
      }
      
      if (comparison === 0) {
        comparison = a.id - b.id
      }
      
      return invSortOrder === "asc" ? comparison : -comparison
    })
  }, [investmentData?.transactions, invSortField, invSortOrder])

  const handleSnapSort = (field: typeof snapSortField) => {
    if (snapSortField === field) {
      setSnapSortOrder(snapSortOrder === "asc" ? "desc" : "asc")
    } else {
      setSnapSortField(field)
      setSnapSortOrder("desc")
    }
  }

  const sortedSnapshots = useMemo(() => {
    return [...(investmentData?.value_series || [])].sort((a, b) => {
      let comparison = 0
      switch (snapSortField) {
        case "date":
          comparison = new Date(a.date).getTime() - new Date(b.date).getTime()
          break
        case "current_value":
          comparison = a.current_value - b.current_value
          break
      }
      
      if (comparison === 0) {
        comparison = a.id - b.id
      }
      
      return snapSortOrder === "asc" ? comparison : -comparison
    })
  }, [investmentData?.value_series, snapSortField, snapSortOrder])

  const handleQuickFilter = (value: string) => {
    const now = new Date()
    switch (value) {
      case "all":
        setDateStart("")
        setDateEnd("")
        break
      case "current-month":
        setDateStart(format(startOfMonth(now), "yyyy-MM-dd"))
        setDateEnd(format(endOfMonth(now), "yyyy-MM-dd"))
        break
      case "last-3-months":
        setDateStart(format(subMonths(now, 3), "yyyy-MM-dd"))
        setDateEnd(format(now, "yyyy-MM-dd"))
        break
      case "current-year":
        setDateStart(format(startOfYear(now), "yyyy-MM-dd"))
        setDateEnd(format(endOfYear(now), "yyyy-MM-dd"))
        break
    }
  }

  // -- Memos --
  const formatValue = (value: number | null | undefined, currencyCode: string = "EUR") => formatCurrencyShared(value, currencyCode)

  const formatCurrency = (value: number) => {
    return formatValue(value, account?.currency || "EUR")
  }

  return { confirm, id, account, setAccount, transferTx, setTransferTx, reconcileOpen, setReconcileOpen, importOpen, setImportOpen, reimbursementTx, setReimbursementTx, splitTx, setSplitTx, allAccounts, setAllAccounts, transactions, setTransactions, hasMoreTx, setHasMoreTx, loadingMoreTx, setLoadingMoreTx, flowSummary, setFlowSummary, knownMerchants, setKnownMerchants, timeseries, setTimeseries, investmentData, setInvestmentData, perfHistory, setPerfHistory, holdings, setHoldings, categories, setCategories, availableTags, setAvailableTags, tagTotals, setTagTotals, loading, setLoading, search, setSearch, debouncedSearch, setDebouncedSearch, dateStart, setDateStart, dateEnd, setDateEnd, sortField, setSortField, sortOrder, setSortOrder, invSortField, setInvSortField, invSortOrder, setInvSortOrder, snapSortField, setSnapSortField, snapSortOrder, setSnapSortOrder, filterType, setFilterType, filterCategory, setFilterCategory, filterMerchant, setFilterMerchant, filterTags, setFilterTags, selectedIds, setSelectedIds, isBulkEditDialogOpen, setIsBulkEditDialogOpen, bulkCategory, setBulkCategory, bulkRecurring, setBulkRecurring, bulkTagIds, setBulkTagIds, bulkTagAction, setBulkTagAction, handleSort, handleInvSort, sortedInvestmentTransactions, handleSnapSort, sortedSnapshots, handleQuickFilter, formatValue, formatCurrency }
}
