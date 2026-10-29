import { toast } from "sonner"
import { useEffect, useState } from "react"
import { BaselineRow, PointZeroModalProps } from "./types"
import { getHoldings, getHoldingsSuggestions, getMarketQuote, getMarketSearch, postEtfProfilesAutoDecompose, postHoldingsBaseline } from "@/lib/api/investments"

/** Lignes du point zéro : suggestions, recherche de titres, édition et enregistrement. */
export function usePointZeroState(p: { open: PointZeroModalProps["open"]; onOpenChange: PointZeroModalProps["onOpenChange"]; accountId: PointZeroModalProps["accountId"]; accountName: PointZeroModalProps["accountName"]; onBaselineSaved: PointZeroModalProps["onBaselineSaved"] }) {
  const { open, onOpenChange, accountId, accountName, onBaselineSaved } = p
  const [rows, setRows] = useState<BaselineRow[]>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [saving, setSaving] = useState(false)

  // Search state
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showSearchDropdown, setShowSearchDropdown] = useState(false)

  // Custom ETF Modal state
  const [customEtfOpen, setCustomEtfOpen] = useState(false)
  const [pendingEtfSearch, setPendingEtfSearch] = useState("")

  // Load suggestions or current holdings when opened
  useEffect(() => {
    if (!open) return

    async function loadInitial() {
      setLoadingSuggestions(true)
      try {
        // First check if account already has holdings
        const existingHoldings = await getHoldings<any[]>(`?account_id=${accountId}`)
        if (existingHoldings && existingHoldings.length > 0) {
          setRows(
            existingHoldings.map((h) => ({
              ticker: h.ticker,
              asset_name: h.asset_name,
              isin: h.isin,
              quantity: h.quantity,
              buy_price_avg: h.buy_price_avg,
              currency: h.currency || "EUR",
              etf_profile_id: h.etf_profile_id,
              is_etf: !!h.is_etf,
              current_price: h.current_price,
              current_price_eur: h.current_price_eur,
            }))
          )
        } else {
          // No holdings yet: load intelligent suggestions from historical notes
          const suggs = await getHoldingsSuggestions<any[]>(`?account_id=${accountId}`)
          if (suggs && suggs.length > 0) {
            const symbols = suggs.map((s) => s.ticker)
            let quotes: any = {}
            try {
              quotes = await getMarketQuote<any>(`?symbols=${symbols.join(",")}`)
            } catch (e) {
              // Ignore quote error on suggestions
            }

            setRows(
              suggs.map((s) => {
                const q = quotes[s.ticker.toUpperCase()] || {}
                return {
                  ticker: s.ticker,
                  asset_name: s.name,
                  isin: s.isin,
                  quantity: 0,
                  buy_price_avg: undefined,
                  currency: q.currency || "EUR",
                  etf_profile_id: s.etf_profile_id,
                  is_etf: !!s.is_etf,
                  current_price: q.price,
                  current_price_eur: q.price_eur,
                  is_suggestion: true,
                }
              })
            )
          }
        }
      } catch (err) {
        console.error("Error loading baseline data:", err)
      } finally {
        setLoadingSuggestions(false)
      }
    }

    loadInitial()
  }, [open, accountId])

  // Handle Search
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([])
      setShowSearchDropdown(false)
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const results = await getMarketSearch<any[]>(`?q=${encodeURIComponent(searchQuery)}`)
        setSearchResults(results || [])
        setShowSearchDropdown(true)
      } catch (err) {
        console.error("Search error:", err)
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  const handleSelectSearchResult = async (item: any) => {
    setShowSearchDropdown(false)
    setSearchQuery("")

    if (rows.some((r) => r.ticker.toUpperCase() === item.symbol.toUpperCase())) {
      toast.info(`${item.symbol} est déjà dans votre liste`)
      return
    }

    let priceEur = undefined
    let price = undefined
    try {
      const qResp = await getMarketQuote<any>(`?symbols=${item.symbol}`)
      const q = qResp[item.symbol.toUpperCase()]
      if (q) {
        price = q.price
        priceEur = q.price_eur
      }
    } catch (e) {}

    const isFundOrEtf = item.type === "ETF" || item.type === "MUTUALFUND" || !!item.etf_profile_id || item.symbol.startsWith("0P")
    let profileId = item.etf_profile_id

    // If it's an ETF or fund without a known profile, auto-decompose it online!
    if (isFundOrEtf && !profileId) {
      try {
        const toastId = toast.loading(`Décomposition de ${item.name || item.symbol} en ligne...`)
        const decomp = await postEtfProfilesAutoDecompose<any>({
          symbol: item.symbol,
          name: item.name,
          isin: item.isin,
        })
        if (decomp && decomp.id) {
          profileId = decomp.id
          toast.success(`${decomp.name} décomposé avec succès !`, { id: toastId })
        } else {
          toast.dismiss(toastId)
        }
      } catch (err) {
        // Fallback silently if offline or unavailable
      }
    }

    const newRow: BaselineRow = {
      ticker: item.symbol,
      asset_name: item.name || item.symbol,
      isin: item.isin,
      quantity: 1,
      currency: item.currency || "EUR",
      etf_profile_id: profileId,
      is_etf: isFundOrEtf,
      current_price: price,
      current_price_eur: priceEur,
    }

    setRows((prev) => [...prev, newRow])
  }

  const handleUpdateRow = (index: number, field: keyof BaselineRow, value: any) => {
    setRows((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }
      return next
    })
  }

  const handleRemoveRow = (index: number) => {
    setRows((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    const validRows = rows.filter((r) => r.quantity > 0)
    if (validRows.length === 0) {
      toast.error("Veuillez renseigner un nombre de parts (> 0) pour au moins un actif")
      return
    }

    setSaving(true)
    try {
      await postHoldingsBaseline({
        account_id: accountId,
        holdings: validRows.map((r) => ({
          ticker: r.ticker,
          asset_name: r.asset_name,
          isin: r.isin,
          quantity: Number(r.quantity),
          buy_price_avg: r.buy_price_avg ? Number(r.buy_price_avg) : undefined,
          currency: r.currency || "EUR",
          etf_profile_id: r.etf_profile_id,
        })),
      })
      toast.success("État des lieux enregistré avec succès")
      onBaselineSaved()
      onOpenChange(false)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur lors de l'enregistrement de l'état des lieux")
    } finally {
      setSaving(false)
    }
  }

  const totalCalculatedEur = rows.reduce((acc, r) => {
    const p = r.current_price_eur || r.buy_price_avg || 0
    return acc + (r.quantity || 0) * p
  }, 0)

  return { rows, setRows, loadingSuggestions, setLoadingSuggestions, saving, setSaving, searchQuery, setSearchQuery, searchResults, setSearchResults, isSearching, setIsSearching, showSearchDropdown, setShowSearchDropdown, customEtfOpen, setCustomEtfOpen, pendingEtfSearch, setPendingEtfSearch, handleSelectSearchResult, handleUpdateRow, handleRemoveRow, handleSave, totalCalculatedEur }
}
