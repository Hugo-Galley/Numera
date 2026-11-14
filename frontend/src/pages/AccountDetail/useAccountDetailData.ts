import { type AccountLite } from "@/types/transfers"
import { PortfolioHolding } from "@/types/diversity"
import { endOfDayParam, startOfDayParam } from "@/lib/dates"
import { errorMessage } from "@/lib/utils"
import { ApiError } from "@/lib/api"
import i18n from "i18next"
import { toast } from "sonner"
import { useEffect, useEffectEvent, useRef, useState } from "react"
import { Account, Category, TagType, Transaction, TX_PAGE_SIZE } from "./types"
import type { useAccountDetailState } from "./useAccountDetailState"
import type { useAccountForms } from "./useAccountForms"
import { getAccounts, getAccountsById } from "@/lib/api/accounts"
import { getAnalyticsAssetAllocationSuggestions, getAnalyticsInvestmentsById, getAnalyticsInvestmentsPerformanceHistory, getAnalyticsTags, getAnalyticsTimeseries } from "@/lib/api/analytics"
import { getCategories, getTags } from "@/lib/api/classement"
import { getHoldings } from "@/lib/api/investments"
import { getTransactions, getTransactionsMerchants } from "@/lib/api/transactions"

/** Chargement du compte et de ses listes (complet au changement de compte, liste seule au changement de filtre). */
export function useAccountDetailData(p: ReturnType<typeof useAccountDetailState> & ReturnType<typeof useAccountForms>) {
  const { id, account, setAccount, setTransferTx, allAccounts, setAllAccounts, transactions, setTransactions, setHasMoreTx, setLoadingMoreTx, setKnownMerchants, setTimeseries, setInvestmentData, setPerfHistory, setHoldings, setCategories, setAvailableTags, setTagTotals, setLoading, search, debouncedSearch, setDebouncedSearch, dateStart, dateEnd, filterType, filterCategory, filterMerchant, filterTags, setTxCurrency, setInvTxCurrency, setSuggestions } = p
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
  // Chargement complet : numéro de requête pour ignorer la réponse d'un compte quitté entre-temps
  const loadRequestId = useRef(0)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [txLoading, setTxLoading] = useState(false)

  const loadTransactions = async (opts?: { reset?: boolean }) => {
    if (!id) return
    const requestId = ++txRequestId.current
    setTxLoading(true)
    try {
      // Garder les pages déjà chargées après une modification (l'API plafonne à 1000) ;
      // un changement de filtre repart de la première page
      const limit = opts?.reset ? TX_PAGE_SIZE : Math.min(Math.max(TX_PAGE_SIZE, transactions.length), 1000)
      const txData = await getTransactions<Transaction[]>(`?${buildTransactionParams(0, limit).toString()}`)
      if (requestId !== txRequestId.current) return
      setTransactions(txData)
      setHasMoreTx(txData.length === limit)
    } catch (error) {
      if (requestId === txRequestId.current) toast.error(errorMessage(error, i18n.t("load.searchError", { ns: "accountDetail" })))
    } finally {
      if (requestId === txRequestId.current) setTxLoading(false)
    }
  }

  /** Même fenêtre que la liste : début de journée → fin de journée (`end_date` est exclusif côté backend). */
  const tagTotalsQuery = () => {
    const params = new URLSearchParams({ account_id: id! })
    if (dateStart) params.append("start_date", startOfDayParam(dateStart))
    if (dateEnd) params.append("end_date", endOfDayParam(dateEnd))
    return `?${params.toString()}`
  }

  const loadTagTotals = async () => {
    if (!id) return
    try {
      setTagTotals(await getAnalyticsTags(tagTotalsQuery()))
    } catch (error) {
      toast.error(errorMessage(error, i18n.t("load.tagsError", { ns: "accountDetail" })))
    }
  }

  const loadMoreTransactions = async () => {
    if (!id) return
    // Même numéro que la liste : un changement de filtre pendant le chargement invalide cette page
    const requestId = txRequestId.current
    setLoadingMoreTx(true)
    try {
      const params = buildTransactionParams(transactions.length)
      const more = await getTransactions<Transaction[]>(`?${params.toString()}`)
      if (requestId !== txRequestId.current) return
      setTransactions(prev => [...prev, ...more])
      setHasMoreTx(more.length === TX_PAGE_SIZE)
    } catch (error) {
      if (requestId === txRequestId.current) toast.error(errorMessage(error, i18n.t("load.txError", { ns: "accountDetail" })))
    } finally {
      setLoadingMoreTx(false)
    }
  }

  const openTransferDialog = async (tx: Transaction) => {
    if (allAccounts.length === 0) {
      try {
        setAllAccounts(await getAccounts<AccountLite[]>())
      } catch {
        toast.error(i18n.t("load.accountsError", { ns: "accountDetail" }))
        return
      }
    }
    setTransferTx(tx)
  }

  // `quiet` : rechargement après une modification, sans remplacer la page par un spinner
  const loadData = async (opts?: { quiet?: boolean }) => {
    if (!id) return
    const requestId = ++loadRequestId.current
    const isCurrent = () => requestId === loadRequestId.current
    if (!opts?.quiet) {
      setLoading(true)
      setLoadError(null)
    }
    try {
      const [accData, merchantsData, suggestionsData] = await Promise.all([
        getAccountsById<Account>(id),
        getTransactionsMerchants<string[]>(),
        getAnalyticsAssetAllocationSuggestions()
      ])
      if (!isCurrent()) return
      setAccount(accData)
      setKnownMerchants(merchantsData)
      if (suggestionsData) setSuggestions(suggestionsData)
      setTxCurrency(accData.currency)
      setInvTxCurrency(accData.currency)

      if (accData.type === "investissement" || accData.type === "assurance_vie") {
        const [invData, perfData, holdingsData] = await Promise.all([
          getAnalyticsInvestmentsById(id),
          getAnalyticsInvestmentsPerformanceHistory(id),
          getHoldings<PortfolioHolding[]>(`?account_id=${id}`)
        ])
        if (!isCurrent()) return
        setInvestmentData(invData)
        setPerfHistory(perfData.items || [])
        setHoldings(holdingsData || [])
      } else {
        const params = buildTransactionParams()

        const [txData, timeData, catData, tagsData, tagTotalsData] = await Promise.all([
          getTransactions<Transaction[]>(`?${params.toString()}`),
          getAnalyticsTimeseries(`?account_id=${id}&year=${new Date().getFullYear()}`),
          getCategories<Category[]>(),
          getTags<TagType[]>(),
          getAnalyticsTags(tagTotalsQuery())
        ])
        if (!isCurrent()) return
        setTransactions(txData)
        setHasMoreTx(txData.length === TX_PAGE_SIZE)
        setTimeseries(timeData)
        setCategories(catData)
        setAvailableTags(tagsData)
        setTagTotals(tagTotalsData)
      }
    } catch (error) {
      if (!isCurrent()) return
      if (error instanceof ApiError && error.status === 404) {
        setAccount(null)
      } else if (opts?.quiet) {
        toast.error(errorMessage(error, i18n.t("load.dataError", { ns: "accountDetail" })))
      } else {
        // Page entière en erreur (avec « Réessayer ») : jamais confondue avec un compte inexistant
        console.error("Failed to load account", error)
        setLoadError(errorMessage(error, i18n.t("load.accountError", { ns: "accountDetail" })))
      }
    } finally {
      if (isCurrent()) setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
    }, 300)
    return () => clearTimeout(timer)
  }, [search, setDebouncedSearch])

  // Les effets ci-dessous se déclenchent sur des valeurs précises mais lisent les dernières fonctions de chargement
  const loadAccountPage = useEffectEvent(() => { loadData() })
  const reloadTransactionList = useEffectEvent(() => {
    if (account && account.type !== "investissement" && account.type !== "assurance_vie") {
      loadTransactions({ reset: true })
    }
  })
  const reloadTagTotals = useEffectEvent(() => {
    if (account && account.type !== "investissement" && account.type !== "assurance_vie") {
      loadTagTotals()
    }
  })

  // Chargement complet : au changement de compte seulement
  useEffect(() => {
    loadAccountPage()
  }, [id])

  // Un changement de filtre ou de recherche ne recharge que la liste (et les totaux par tag) :
  // la page, ses dialogues, le défilement et les filtres restent en place
  useEffect(() => {
    reloadTransactionList()
  }, [debouncedSearch, filterType, filterCategory, filterMerchant, filterTags, dateStart, dateEnd])

  useEffect(() => {
    reloadTagTotals()
  }, [dateStart, dateEnd])

  return { buildTransactionParams, txRequestId, txLoading, setTxLoading, loadTransactions, loadTagTotals, loadMoreTransactions, openTransferDialog, loadData, loadError }
}
