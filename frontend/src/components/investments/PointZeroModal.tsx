import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { 
  Trash2, 
  Plus, 
  Search, 
  Layers, 
  CheckCircle2, 
  SlidersHorizontal,
  X,
  Loader2
} from "lucide-react"
import { CustomEtfModal } from "./CustomEtfModal"
import { CompanyLogo } from "@/components/ui/CompanyLogo"

interface BaselineRow {
  ticker: string
  asset_name: string
  isin?: string
  quantity: number
  buy_price_avg?: number
  currency: string
  etf_profile_id?: number
  is_etf: boolean
  current_price?: number
  current_price_eur?: number
  is_suggestion?: boolean
}

interface PointZeroModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  accountId: number
  accountName: string
  onBaselineSaved: () => void
}

export function PointZeroModal({
  open,
  onOpenChange,
  accountId,
  accountName,
  onBaselineSaved,
}: PointZeroModalProps) {
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
        const existingHoldings = await api.get<any[]>(`/holdings?account_id=${accountId}`)
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
          const suggs = await api.get<any[]>(`/holdings/suggestions?account_id=${accountId}`)
          if (suggs && suggs.length > 0) {
            const symbols = suggs.map((s) => s.ticker)
            let quotes: any = {}
            try {
              quotes = await api.get<any>(`/market/quote?symbols=${symbols.join(",")}`)
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
        const results = await api.get<any[]>(`/market/search?q=${encodeURIComponent(searchQuery)}`)
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
      const qResp = await api.get<any>(`/market/quote?symbols=${item.symbol}`)
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
        const decomp = await api.post<any>("/etf-profiles/auto-decompose", {
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
      await api.post("/holdings/baseline", {
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

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col p-6">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="h-5 w-5 text-slate-800" />
              <DialogTitle className="text-lg font-bold text-slate-900">Point Zéro : {accountName}</DialogTitle>
            </div>
            <DialogDescription className="text-xs text-slate-500">
              Déclarez vos positions actuelles. Les cours boursiers en direct valoriseront automatiquement votre portefeuille sans altérer vos transactions passées.
            </DialogDescription>
          </DialogHeader>

          {/* Search bar */}
          <div className="relative mt-2">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Rechercher par Code ISIN, Ticker (ex: CW8.PA, AAPL) ou Nom..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-8 text-sm bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 shadow-2xs focus-visible:ring-1 focus-visible:ring-slate-400"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery("")
                      setSearchResults([])
                      setShowSearchDropdown(false)
                    }}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                className="shrink-0 gap-1.5 text-xs h-9 border-slate-200 text-slate-700 hover:bg-slate-50"
                onClick={() => {
                  setPendingEtfSearch(searchQuery)
                  setCustomEtfOpen(true)
                }}
              >
                <Plus className="h-3.5 w-3.5" />
                Créer un ETF
              </Button>
            </div>

            {/* Search Dropdown */}
            {showSearchDropdown && (
              <div className="absolute top-full left-0 right-0 z-50 mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl max-h-72 overflow-y-auto divide-y divide-slate-100">
                {isSearching ? (
                  <div className="p-4 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-400" />
                    <span>Recherche sur les marchés en cours...</span>
                  </div>
                ) : searchResults.length > 0 ? (
                  <div className="divide-y divide-slate-100">
                    {searchResults.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-3 hover:bg-slate-50 cursor-pointer flex items-center justify-between transition-colors text-xs"
                        onClick={() => handleSelectSearchResult(item)}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <CompanyLogo
                            ticker={item.symbol}
                            name={item.name}
                            isin={item.isin}
                            className="h-7 w-7 rounded-md shrink-0 shadow-2xs"
                          />
                          <div className="flex flex-col min-w-0">
                            <span className="font-semibold text-slate-900 text-xs truncate max-w-[280px]">
                              {item.name || item.symbol}
                            </span>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="font-mono text-[10px] text-slate-400 font-medium">
                                {item.symbol}
                              </span>
                              {item.isin && (
                                <span className="font-mono text-[10px] text-slate-400">
                                  • {item.isin}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <Badge variant="secondary" className="bg-slate-100 text-slate-700 text-[10px] px-1.5 py-0 font-normal">
                            {item.type || (item.is_etf ? "ETF" : "Action")}
                          </Badge>
                          {item.etf_profile_id && (
                            <Badge variant="outline" className="text-[9px] px-1.5 py-0 font-normal text-emerald-700 bg-emerald-50 border-emerald-200">
                              Profil ETF inclus
                            </Badge>
                          )}
                          <span className="text-[10px] text-slate-400 font-mono">
                            {item.exchange || item.currency}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 text-center space-y-2">
                    <p className="text-xs text-slate-500">Aucun résultat trouvé pour "{searchQuery}".</p>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs gap-1.5"
                      onClick={() => {
                        setShowSearchDropdown(false)
                        setPendingEtfSearch(searchQuery)
                        setCustomEtfOpen(true)
                      }}
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Définir cet ETF personnalisé
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Table of Rows */}
          <div className="flex-1 overflow-y-auto mt-4 border border-slate-200 rounded-lg bg-white">
            {loadingSuggestions ? (
              <div className="p-8 text-center text-sm text-slate-500 flex flex-col items-center gap-2">
                <div className="h-5 w-5 rounded-full border-2 border-slate-300 border-t-slate-900 animate-spin" />
                <span className="text-xs">Détection automatique de vos actifs...</span>
              </div>
            ) : rows.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500 space-y-2">
                <Layers className="h-7 w-7 text-slate-300 mx-auto" />
                <p className="font-medium text-xs text-slate-700">Aucun actif dans cet état des lieux.</p>
                <p className="text-[11px] text-slate-400">Recherchez vos actions et ETFs ci-dessus pour les ajouter.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                <div className="grid grid-cols-12 gap-2 px-3 py-2 text-xs font-semibold text-slate-500 bg-slate-50/80 border-b border-slate-100">
                  <div className="col-span-5">Actif / Symbole</div>
                  <div className="col-span-2 text-right">Cours Réel</div>
                  <div className="col-span-2 text-right">Nombre de parts</div>
                  <div className="col-span-2 text-right">Valeur Estimée</div>
                  <div className="col-span-1 text-center"></div>
                </div>

                {rows.map((row, idx) => {
                  const unitPrice = row.current_price_eur || row.buy_price_avg || 0
                  const rowVal = (row.quantity || 0) * unitPrice

                  return (
                    <div
                      key={idx}
                      className="grid grid-cols-12 gap-2 px-3 py-2 items-center hover:bg-slate-50/60 transition-colors"
                    >
                      <div className="col-span-5 flex items-center gap-2.5 min-w-0 pr-2">
                        <CompanyLogo
                          ticker={row.ticker}
                          name={row.asset_name}
                          isin={row.isin}
                          className="h-7 w-7 rounded-md shrink-0 shadow-2xs"
                        />
                        <div className="flex flex-col min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-semibold text-xs text-slate-900 truncate">
                              {row.asset_name || row.ticker}
                            </span>
                            {row.is_etf ? (
                              <Badge variant="secondary" className="bg-slate-100 text-slate-700 text-[9px] px-1 py-0 font-normal">
                                ETF
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 font-normal text-slate-500 border-slate-200">
                                Action
                              </Badge>
                            )}
                            {row.is_suggestion && row.quantity === 0 && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 font-normal text-amber-700 bg-amber-50 border-amber-200">
                                Suggéré
                              </Badge>
                            )}
                          </div>
                          <span className="font-mono text-[10px] text-slate-400 truncate">
                            {row.ticker}{row.isin ? ` • ${row.isin}` : ""}
                          </span>
                        </div>
                      </div>

                      <div className="col-span-2 text-right">
                        {row.current_price ? (
                          <div className="flex flex-col items-end">
                            <span className="font-mono text-xs font-medium text-slate-800">
                              {row.current_price.toFixed(2)} {row.currency}
                            </span>
                            {row.currency !== "EUR" && row.current_price_eur && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                (~{row.current_price_eur.toFixed(2)} €)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">-</span>
                        )}
                      </div>

                      <div className="col-span-2 text-right">
                        <Input
                          type="number"
                          step="any"
                          min="0"
                          placeholder="0"
                          value={row.quantity || ""}
                          onChange={(e) => handleUpdateRow(idx, "quantity", parseFloat(e.target.value) || 0)}
                          className="h-8 text-right font-mono text-xs bg-white border-slate-200 text-slate-900 focus-visible:ring-1 focus-visible:ring-slate-400"
                        />
                      </div>

                      <div className="col-span-2 text-right font-mono text-xs font-semibold text-slate-900">
                        {new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(rowVal)}
                      </div>

                      <div className="col-span-1 text-center">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                          onClick={() => handleRemoveRow(idx)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Footer summary */}
          <div className="flex items-center justify-between pt-4 border-t mt-4">
            <div className="flex flex-col">
              <span className="text-xs text-slate-500">Valeur totale estimée :</span>
              <span className="text-base font-bold font-mono text-slate-900">
                {new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(totalCalculatedEur)}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={saving} className="border-slate-200 text-slate-700">
                Annuler
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleSave}
                disabled={saving}
                className="gap-2 bg-slate-900 hover:bg-slate-800 text-white shadow-sm"
              >
                <CheckCircle2 className="h-4 w-4" />
                {saving ? "Enregistrement..." : "Enregistrer l'état des lieux"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal for creating custom ETF */}
      <CustomEtfModal
        open={customEtfOpen}
        onOpenChange={setCustomEtfOpen}
        initialTicker={pendingEtfSearch}
        initialName={pendingEtfSearch}
        onProfileCreated={(profile) => {
          handleSelectSearchResult({
            symbol: profile.ticker,
            name: profile.name,
            isin: profile.isin,
            type: "ETF",
            currency: "EUR",
            etf_profile_id: profile.id,
          })
        }}
      />
    </>
  )
}
