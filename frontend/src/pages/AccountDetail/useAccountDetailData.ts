import { type AccountLite } from "@/types/transfers"
import { PortfolioHolding } from "@/types/diversity"
import { api } from "@/lib/api"
import { endOfDayParam, startOfDayParam } from "@/lib/dates"
import { errorMessage } from "@/lib/utils"
import { toast } from "sonner"
import { useEffect, useRef, useState } from "react"
import { Account, Category, TagType, Transaction, TX_PAGE_SIZE } from "./types"
import type { useAccountDetailState } from "./useAccountDetailState"
import type { useAccountForms } from "./useAccountForms"

/** Chargement du compte et de ses listes (complet au changement de compte, liste seule au changement de filtre). */
export function useAccountDetailData(p: ReturnType<typeof useAccountDetailState> & ReturnType<typeof useAccountForms>) {
  const { id, account, setAccount, setTransferTx, allAccounts, setAllAccounts, transactions, setTransactions, setHasMoreTx, setLoadingMoreTx, setKnownMerchants, timeseries, setTimeseries, setInvestmentData, setPerfHistory, holdings, setHoldings, categories, setCategories, setAvailableTags, setTagTotals, setLoading, search, debouncedSearch, setDebouncedSearch, dateStart, dateEnd, filterType, filterCategory, filterMerchant, filterTags, setTxCurrency, setInvTxCurrency, suggestions, setSuggestions } = p
  const buildTransactionParams = (skip = 0, limit = TX_PAGE_SIZE) => {
    const params = new URLSearchParams()
    params.append("account_id", id!)
    if (filterType !== "all") params.append("type", filterType)
    if (filterCategory !== "all") params.append("category_id", filterCategory)
    if (filterMerchant !== "all") params.append("merchant", filterMerchant)
    if (dateStart) params.append("start_date", startOfDayParam(dateStart))
    if (dateEnd) params.append("end_date", endOfDayParam(dateEnd))
    if (filterTags.length > 0) {
      filterTags.forEach(tid => params.append("tag_ids", String(tid)))
    }
    if (debouncedSearch) params.append("search", debouncedSearch)
    params.append("skip", String(skip))
    params.append("limit", String(limit))
    return params
  }

  // Numéro de la dernière requête de liste : une réponse arrivée après une autre plus récente est ignorée
  const txRequestId = useRef(0)
  const [txLoading, setTxLoading] = useState(false)

  const loadTransactions = async (opts?: { reset?: boolean }) => {
    if (!id) return
    const requestId = ++txRequestId.current
    setTxLoading(true)
    try {
      // Garder les pages déjà chargées après une modification (l'API plafonne à 1000) ;
      // un changement de filtre repart de la première page
      const limit = opts?.reset ? TX_PAGE_SIZE : Math.min(Math.max(TX_PAGE_SIZE, transactions.length), 1000)
      const txData = await api.get<Transaction[]>(`/transactions?${buildTransactionParams(0, limit).toString()}`)
      if (requestId !== txRequestId.current) return
      setTransactions(txData)
      setHasMoreTx(txData.length === limit)
    } catch (error) {
      if (requestId === txRequestId.current) toast.error(errorMessage(error, "Erreur lors de la recherche"))
    } finally {
      if (requestId === txRequestId.current) setTxLoading(false)
    }
  }

  const loadTagTotals = async () => {
    if (!id) return
    try {
      setTagTotals(await api.get<any[]>(`/analytics/tags?account_id=${id}${dateStart ? `&start_date=${dateStart}` : ""}${dateEnd ? `&end_date=${dateEnd}` : ""}`))
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors du chargement des tags"))
    }
  }

  const loadMoreTransactions = async () => {
    if (!id) return
    setLoadingMoreTx(true)
    try {
      const params = buildTransactionParams(transactions.length)
      const more = await api.get<Transaction[]>(`/transactions?${params.toString()}`)
      setTransactions(prev => [...prev, ...more])
      setHasMoreTx(more.length === TX_PAGE_SIZE)
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors du chargement des transactions"))
    } finally {
      setLoadingMoreTx(false)
    }
  }

  const openTransferDialog = async (tx: Transaction) => {
    if (allAccounts.length === 0) {
      try {
        setAllAccounts(await api.get<AccountLite[]>("/accounts"))
      } catch {
        toast.error("Erreur lors du chargement des comptes")
        return
      }
    }
    setTransferTx(tx)
  }

  // `quiet` : rechargement après une modification, sans remplacer la page par un spinner
  const loadData = async (opts?: { quiet?: boolean }) => {
    if (!id) return
    if (!opts?.quiet) setLoading(true)
    try {
      const [accData, merchantsData, suggestionsData] = await Promise.all([
        api.get<Account>(`/accounts/${id}`),
        api.get<string[]>("/transactions/merchants"),
        api.get<any>("/analytics/asset-allocation/suggestions")
      ])
      setAccount(accData)
      setKnownMerchants(merchantsData)
      if (suggestionsData) setSuggestions(suggestionsData)
      setTxCurrency(accData.currency)
      setInvTxCurrency(accData.currency)

      if (accData.type === "investissement" || accData.type === "assurance_vie") {
        const [invData, perfData, holdingsData] = await Promise.all([
          api.get<any>(`/analytics/investments/${id}`),
          api.get<any>(`/analytics/investments/${id}/performance-history`),
          api.get<PortfolioHolding[]>(`/holdings?account_id=${id}`)
        ])
        setInvestmentData(invData)
        setPerfHistory(perfData.items || [])
        setHoldings(holdingsData || [])
      } else {
        const params = buildTransactionParams()

        const [txData, timeData, catData, tagsData, tagTotalsData] = await Promise.all([
          api.get<Transaction[]>(`/transactions?${params.toString()}`),
          api.get<any>(`/analytics/timeseries?account_id=${id}&year=${new Date().getFullYear()}`),
          api.get<Category[]>("/categories"),
          api.get<TagType[]>("/tags"),
          api.get<any[]>(`/analytics/tags?account_id=${id}${dateStart ? `&start_date=${dateStart}` : ""}${dateEnd ? `&end_date=${dateEnd}` : ""}`)
        ])
        setTransactions(txData)
        setHasMoreTx(txData.length === TX_PAGE_SIZE)
        setTimeseries(timeData)
        setCategories(catData)
        setAvailableTags(tagsData)
        setTagTotals(tagTotalsData)
      }
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors du chargement des données"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  // Chargement complet : au changement de compte seulement
  useEffect(() => {
    loadData()
  }, [id])

  // Un changement de filtre ou de recherche ne recharge que la liste (et les totaux par tag) :
  // la page, ses dialogues, le défilement et les filtres restent en place
  useEffect(() => {
    if (account && account.type !== "investissement" && account.type !== "assurance_vie") {
      loadTransactions({ reset: true })
    }
  }, [debouncedSearch, filterType, filterCategory, filterMerchant, filterTags, dateStart, dateEnd])

  useEffect(() => {
    if (account && account.type !== "investissement" && account.type !== "assurance_vie") {
      loadTagTotals()
    }
  }, [dateStart, dateEnd])

  return { buildTransactionParams, txRequestId, txLoading, setTxLoading, loadTransactions, loadTagTotals, loadMoreTransactions, openTransferDialog, loadData }
}
