import { useState, useMemo } from "react"
import { PortfolioHolding } from "@/types/diversity"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { Calculator, Check, Pencil, SlidersHorizontal, Trash2, Globe, Layers, Search, X, Coins, CalendarCheck } from "lucide-react"
import { PointZeroModal } from "./PointZeroModal"
import { CostEstimateDialog } from "./CostEstimateDialog"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { cn } from "@/lib/utils"
import { useUI } from "@/providers/UIProvider"
import { useConfirm } from "@/providers/ConfirmProvider"

type TypeFilter = "all" | "action" | "etf"
type PerfFilter = "all" | "gain" | "loss"

interface HoldingsTableProps {
  accountId: number
  accountName: string
  holdings: PortfolioHolding[]
  onRefresh: () => void
  onAddDividend?: (holding: PortfolioHolding) => void
}

export function HoldingsTable({
  accountId,
  accountName,
  holdings,
  onRefresh,
  onAddDividend,
}: HoldingsTableProps) {
  const confirm = useConfirm()
  const [pointZeroOpen, setPointZeroOpen] = useState(false)
  const [costEstimateOpen, setCostEstimateOpen] = useState(false)
  const [editingCostId, setEditingCostId] = useState<number | null>(null)
  const [costDraft, setCostDraft] = useState("")
  const [decomposingId, setDecomposingId] = useState<number | null>(null)
  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all")
  const [perfFilter, setPerfFilter] = useState<PerfFilter>("all")
  // Paramètres → Système : affichage limité au titre et au nombre de parts
  const { hideHoldingValues } = useUI()

  const filteredHoldings = useMemo(() => {
    return holdings.filter((h) => {
      // Text search
      if (search.trim().length >= 1) {
        const q = search.toLowerCase()
        if (
          !h.asset_name?.toLowerCase().includes(q) &&
          !h.ticker?.toLowerCase().includes(q) &&
          !h.isin?.toLowerCase().includes(q)
        ) return false
      }
      // Type filter
      if (typeFilter === "etf" && !h.is_etf && !h.etf_profile_id) return false
      if (typeFilter === "action" && (h.is_etf || h.etf_profile_id)) return false
      // Perf filter
      if (!hideHoldingValues && perfFilter === "gain" && (h.gain_eur === undefined || h.gain_eur === null || h.gain_eur < 0)) return false
      if (!hideHoldingValues && perfFilter === "loss" && (h.gain_eur === undefined || h.gain_eur === null || h.gain_eur >= 0)) return false
      return true
    })
  }, [holdings, search, typeFilter, perfFilter, hideHoldingValues])

  const hasActiveFilters = search.trim().length > 0 || typeFilter !== "all" || (!hideHoldingValues && perfFilter !== "all")

  const handleDecompose = async (h: PortfolioHolding) => {
    setDecomposingId(h.id)
    const toastId = toast.loading(`Décomposition de ${h.ticker} en ligne...`)
    try {
      const res = await api.post<any>("/etf-profiles/auto-decompose", {
        symbol: h.ticker,
        name: h.asset_name,
        isin: h.isin,
      })
      if (res && res.id) {
        await api.put(`/holdings/${h.id}`, {
          etf_profile_id: res.id,
          is_etf: true,
        })
        toast.success(`${res.name} décomposé avec succès !`, { id: toastId })
        onRefresh()
      } else {
        toast.error("Impossible de décomposer ce fonds en ligne", { id: toastId })
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur de décomposition", { id: toastId })
    } finally {
      setDecomposingId(null)
    }
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(val)
  }

  const totalValue = filteredHoldings.reduce((acc, h) => acc + (h.current_value_eur || 0), 0)

  const handleDelete = async (holdingId: number, name: string) => {
    if (!(await confirm(`Supprimer la position sur ${name} ?`))) return
    try {
      await api.delete(`/holdings/${holdingId}`)
      toast.success("Position supprimée")
      onRefresh()
    } catch (err: any) {
      toast.error(err?.message || "Erreur lors de la suppression")
    }
  }

  const handleTogglePaysDividends = async (h: PortfolioHolding) => {
    try {
      await api.put(`/holdings/${h.id}`, { pays_dividends: !h.pays_dividends })
      toast.success(h.pays_dividends ? `${h.ticker} : ne distribue pas` : `${h.ticker} : titre distribuant (rappel si aucun dividende pendant 13 mois)`)
      onRefresh()
    } catch (err: any) {
      toast.error(err?.message || "Erreur lors de la mise à jour")
    }
  }

  const startEditCost = (h: PortfolioHolding) => {
    setEditingCostId(h.id)
    setCostDraft(h.buy_price_avg ? String(h.buy_price_avg) : "")
  }

  const saveCost = async (h: PortfolioHolding) => {
    const value = Number(costDraft.replace(",", "."))
    if (costDraft.trim() !== "" && !(value > 0)) {
      toast.error("Le PRU doit être un nombre positif")
      return
    }
    try {
      // Vide = PRU inconnu ; le backend modifie la ligne du Point Zéro puis recalcule les positions
      await api.put(`/holdings/${h.id}`, { buy_price_avg: costDraft.trim() === "" ? null : value })
      toast.success(`PRU de ${h.ticker} mis à jour`)
      setEditingCostId(null)
      onRefresh()
    } catch (err: any) {
      toast.error(err?.message || "Impossible de modifier le PRU")
    }
  }

  const resetFilters = () => {
    setSearch("")
    setTypeFilter("all")
    setPerfFilter("all")
  }

  return (
    <>
      <Card className="shadow-sm">
        <CardHeader className="flex flex-col gap-4 pb-4 border-b">
          {/* Title + action button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Layers className="h-5 w-5 text-slate-500" />
                <CardTitle className="text-base font-bold md:text-lg">Positions Actuelles (Actions & ETFs)</CardTitle>
              </div>
              <CardDescription className="text-sm mt-1">
                {hideHoldingValues
                  ? "Titres détenus et nombre de parts."
                  : "Valorisation en direct de vos lignes boursières au cours de marché."}
              </CardDescription>
            </div>
            <div className="flex flex-col gap-2 shrink-0 sm:flex-row sm:flex-wrap">
              {!hideHoldingValues && holdings.some((h) => !h.buy_price_avg) && (
                <Button size="sm" variant="outline" onClick={() => setCostEstimateOpen(true)} className="h-10 gap-2 md:h-9">
                  <Calculator className="h-4 w-4" />
                  Estimer les PRU
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => setPointZeroOpen(true)}
                className="h-10 gap-2 md:h-9"
              >
                <SlidersHorizontal className="h-4 w-4" />
                Point Zéro / État des Lieux
              </Button>
            </div>
          </div>

          {/* Filter bar — only shown when there are holdings */}
          {holdings.length > 0 && (
            <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
                <Input
                  placeholder="Nom, ticker, ISIN…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="h-10 pl-8 text-base md:h-8 md:text-sm bg-slate-50 border-slate-200 focus-visible:ring-1 focus-visible:ring-slate-300"
                />
                {search && (
                  <button
                    onClick={() => setSearch("")}
                    className="absolute right-0 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center text-slate-400 hover:text-slate-600 md:right-2 md:h-auto md:w-auto"
                    aria-label="Effacer la recherche"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* Type filter */}
              <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1 shrink-0 overflow-x-auto">
                {(["all", "action", "etf"] as TypeFilter[]).map((v) => (
                  <button
                    key={v}
                    onClick={() => setTypeFilter(v)}
                    className={cn(
                      "flex-1 whitespace-nowrap px-2.5 py-2 md:py-1 rounded-md text-xs font-semibold transition-all",
                      typeFilter === v
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    )}
                  >
                    {v === "all" ? "Tous" : v === "action" ? "Actions" : "ETFs"}
                  </button>
                ))}
              </div>

              {/* Perf filter */}
              {!hideHoldingValues && (
              <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1 shrink-0 overflow-x-auto">
                {(["all", "gain", "loss"] as PerfFilter[]).map((v) => (
                  <button
                    key={v}
                    onClick={() => setPerfFilter(v)}
                    className={cn(
                      "flex-1 whitespace-nowrap px-2.5 py-2 md:py-1 rounded-md text-xs font-semibold transition-all",
                      perfFilter === v && v === "all" && "bg-white text-slate-900 shadow-sm",
                      perfFilter === v && v === "gain" && "bg-white text-emerald-600 shadow-sm",
                      perfFilter === v && v === "loss" && "bg-white text-rose-600 shadow-sm",
                      perfFilter !== v && "text-slate-500 hover:text-slate-700",
                    )}
                  >
                    {v === "all" ? "Tous" : v === "gain" ? "📈 En gain" : "📉 En perte"}
                  </button>
                ))}
              </div>
              )}

              {/* Reset */}
              {hasActiveFilters && (
                <button
                  onClick={resetFilters}
                  className="text-xs text-slate-500 hover:text-slate-600 transition-colors shrink-0 flex items-center justify-center gap-1 min-h-10 md:min-h-0"
                >
                  <X className="h-3 w-3" /> Réinitialiser
                </button>
              )}
            </div>
          )}
        </CardHeader>

        <CardContent className="p-0">
          {holdings.length === 0 ? (
            <div className="p-10 text-center space-y-3">
              <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Layers className="h-6 w-6" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h4 className="font-semibold text-base text-slate-900">Aucune position active renseignée</h4>
                <p className="text-sm text-slate-500">
                  Définissez votre <strong>Point Zéro</strong> en indiquant le nombre de parts détenues. Numera valorise vos positions au cours réel du marché.
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setPointZeroOpen(true)}
                className="gap-2 mt-2"
              >
                <SlidersHorizontal className="h-4 w-4" />
                Définir l'état des lieux
              </Button>
            </div>
          ) : filteredHoldings.length === 0 ? (
            /* Empty state when filters return nothing */
            <div className="py-12 text-center">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 mb-3 text-slate-300">
                <Search className="h-5 w-5" />
              </div>
              <p className="text-slate-500 font-medium text-sm">Aucune position ne correspond aux filtres</p>
              <button
                onClick={resetFilters}
                className="mt-2 text-xs text-slate-400 hover:text-slate-600 underline underline-offset-2 transition-colors"
              >
                Réinitialiser les filtres
              </button>
            </div>
          ) : (
            <div>
              {hasActiveFilters && (
                <div className="px-4 py-2 text-xs text-slate-400 border-b bg-slate-50/50">
                  {filteredHoldings.length} résultat{filteredHoldings.length > 1 ? "s" : ""} sur {holdings.length} position{holdings.length > 1 ? "s" : ""}
                </div>
              )}

              {/* Mobile : une carte par position */}
              <ul className="divide-y md:hidden">
                {filteredHoldings.map((h) => {
                  const weightPct = totalValue > 0 ? ((h.current_value_eur || 0) / totalValue) * 100 : 0
                  const isEtf = h.is_etf || h.etf_profile_id
                  const gainColor = (h.gain_eur ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600"
                  return (
                    <li key={h.id} className="space-y-3 p-4">
                      <div className="flex items-start gap-3">
                        <CompanyLogo ticker={h.ticker} name={h.asset_name} isin={h.isin} className="h-10 w-10 shrink-0 rounded-lg" />
                        <div className="min-w-0 flex-1">
                          <div className="break-words text-sm font-bold leading-snug text-slate-900">{h.asset_name || h.ticker}</div>
                          <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 font-mono text-xs text-slate-500">
                            <span>{h.ticker}</span>
                            {h.isin && <span className="text-[11px] text-slate-400">{h.isin}</span>}
                          </div>
                        </div>
                        <Badge variant={isEtf ? "secondary" : "outline"} className="shrink-0 text-xs font-normal">
                          {isEtf ? (h.etf_profile_id ? "ETF décomposé" : "ETF") : "Action"}
                        </Badge>
                      </div>

                      {hideHoldingValues ? (
                        <div className="flex items-baseline justify-between text-sm">
                          <span className="text-slate-500">Parts</span>
                          <span className="font-mono font-semibold">{Number(h.quantity.toFixed(4))}</span>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-end justify-between gap-3">
                            <div className="min-w-0">
                              <div className="text-xs text-slate-500">Valeur totale</div>
                              <div className="whitespace-nowrap font-mono text-xl font-bold tabular-nums text-slate-900">
                                <span className="amount-blur">{formatCurrency(h.current_value_eur || 0)}</span>
                              </div>
                            </div>
                            {h.gain_eur !== undefined && h.gain_eur !== null && (
                              <div className={cn("shrink-0 text-right font-mono font-semibold tabular-nums", gainColor)}>
                                <div className="amount-blur whitespace-nowrap text-sm">
                                  {h.gain_eur >= 0 ? "+" : ""}{formatCurrency(h.gain_eur)}
                                </div>
                                <div className="text-xs">({h.gain_eur >= 0 ? "+" : ""}{h.gain_pct}%)</div>
                              </div>
                            )}
                          </div>

                          <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 rounded-lg bg-slate-50 p-3 text-xs">
                            <div>
                              <dt className="text-slate-500">Parts</dt>
                              <dd className="font-mono text-sm font-medium tabular-nums">{Number(h.quantity.toFixed(4))}</dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">Poids</dt>
                              <dd className="font-mono text-sm font-medium tabular-nums">{weightPct.toFixed(1)}%</dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">Cours actuel</dt>
                              <dd className="font-mono text-sm tabular-nums">
                                {h.current_price ? (
                                  <>
                                    <span className="whitespace-nowrap font-medium">{formatCurrency(h.current_price_eur || h.current_price)}</span>
                                    {h.price_date && (
                                      <span className={cn("block text-[10px] font-normal", h.price_stale ? "text-amber-600" : "text-slate-400")}>
                                        {h.price_stale ? "⚠ " : ""}{new Date(h.price_date).toLocaleDateString("fr-FR")}
                                      </span>
                                    )}
                                  </>
                                ) : (
                                  <span className="italic text-slate-400">-</span>
                                )}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">Investi</dt>
                              <dd className="font-mono text-sm tabular-nums">
                                {h.total_invested_eur != null ? (
                                  <span className="amount-blur whitespace-nowrap">{formatCurrency(h.total_invested_eur)}</span>
                                ) : (
                                  <span className="italic text-slate-400">-</span>
                                )}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">PRU</dt>
                              <dd className="font-mono text-sm">
                                {editingCostId === h.id ? (
                                  <div className="flex items-center gap-1">
                                    <Input
                                      autoFocus
                                      type="text"
                                      inputMode="decimal"
                                      value={costDraft}
                                      onChange={(e) => setCostDraft(e.target.value)}
                                      onKeyDown={(e) => {
                                        if (e.key === "Enter") saveCost(h)
                                        if (e.key === "Escape") setEditingCostId(null)
                                      }}
                                      className="h-10 w-full min-w-0 text-base"
                                      placeholder={`PRU (${h.currency})`}
                                    />
                                    <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 text-emerald-600" onClick={() => saveCost(h)} aria-label="Enregistrer">
                                      <Check className="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 text-slate-400" onClick={() => setEditingCostId(null)} aria-label="Annuler">
                                      <X className="h-4 w-4" />
                                    </Button>
                                  </div>
                                ) : (
                                  <button type="button" onClick={() => startEditCost(h)} className="-my-2 inline-flex min-h-10 items-center gap-1.5 text-left">
                                    {h.buy_price_avg ? (
                                      <span className="whitespace-nowrap text-slate-700">{h.buy_price_avg.toFixed(2)} {h.currency}</span>
                                    ) : (
                                      <span className="text-xs italic text-amber-600">à renseigner</span>
                                    )}
                                    <Pencil className="h-3 w-3 text-slate-400" />
                                  </button>
                                )}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-slate-500">Dividendes reçus</dt>
                              <dd className="font-mono text-sm tabular-nums">
                                {(h.dividends_received_eur ?? 0) > 0 ? (
                                  <span className="amount-blur whitespace-nowrap font-semibold">{formatCurrency(h.dividends_received_eur!)}</span>
                                ) : (
                                  <span className="italic text-slate-400">-</span>
                                )}
                              </dd>
                            </div>
                            {h.total_return_eur !== undefined && h.total_return_eur !== null && (
                              <div className="col-span-2 flex items-baseline justify-between border-t pt-2.5">
                                <dt className="text-slate-500">Rendement total</dt>
                                <dd className={cn("font-mono text-sm font-semibold tabular-nums", h.total_return_eur >= 0 ? "text-emerald-600" : "text-rose-600")}>
                                  <span className="amount-blur whitespace-nowrap">{h.total_return_eur >= 0 ? "+" : ""}{formatCurrency(h.total_return_eur)}</span>{" "}
                                  <span className="text-xs">({h.total_return_eur >= 0 ? "+" : ""}{h.total_return_pct}%)</span>
                                </dd>
                              </div>
                            )}
                          </dl>
                        </>
                      )}

                      <div className="flex items-center justify-end gap-1">
                        {onAddDividend && (
                          <Button variant="ghost" size="icon" className="h-10 w-10 text-slate-500 hover:text-emerald-600" onClick={() => onAddDividend(h)} aria-label="Saisir un dividende">
                            <Coins className="h-5 w-5" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className={cn("h-10 w-10", h.pays_dividends ? "text-emerald-600 hover:text-emerald-700" : "text-slate-400 hover:text-slate-600")}
                          onClick={() => handleTogglePaysDividends(h)}
                          aria-label={h.pays_dividends ? "Titre distribuant : désactiver le rappel" : "Marquer comme titre distribuant"}
                        >
                          <CalendarCheck className="h-5 w-5" />
                        </Button>
                        {!h.etf_profile_id && (h.is_etf || h.ticker.startsWith("0P")) && (
                          <Button variant="ghost" size="icon" className="h-10 w-10 text-slate-500 hover:text-slate-900" onClick={() => handleDecompose(h)} disabled={decomposingId === h.id} aria-label="Décomposer en ligne">
                            <Globe className="h-5 w-5" />
                          </Button>
                        )}
                        <Button variant="ghost" size="icon" className="h-10 w-10 text-slate-400 hover:text-rose-600" onClick={() => handleDelete(h.id, h.asset_name)} aria-label="Supprimer la position">
                          <Trash2 className="h-5 w-5" />
                        </Button>
                      </div>
                    </li>
                  )
                })}
              </ul>

              {/* Bureau : tableau */}
              <div className="hidden overflow-x-auto md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="font-semibold text-slate-600">Actif / Symbole</TableHead>
                    <TableHead className="font-semibold text-slate-600">Type</TableHead>
                    <TableHead className="text-right font-semibold text-slate-600">Parts</TableHead>
                    {!hideHoldingValues && (
                      <>
                      <TableHead className="text-right font-semibold text-slate-600" title="Prix de revient unitaire moyen, frais inclus">PRU</TableHead>
                      <TableHead className="text-right font-semibold text-slate-600">Cours actuel</TableHead>
                      <TableHead className="text-right font-semibold text-slate-600" title="Coût de revient en EUR (taux de change des achats)">Investi</TableHead>
                      <TableHead className="text-right font-semibold text-slate-600">Valeur totale</TableHead>
                      <TableHead className="text-right font-semibold text-slate-600">Plus-value latente</TableHead>
                      <TableHead className="text-right font-semibold text-slate-600">Dividendes reçus</TableHead>
                      <TableHead className="text-right font-semibold text-slate-600">Rendement total</TableHead>
                      <TableHead className="text-right font-semibold text-slate-600">Poids</TableHead>
                      </>
                    )}
                    <TableHead className="text-right w-[90px] font-semibold text-slate-600">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredHoldings.map((h) => {
                    const weightPct = totalValue > 0 ? ((h.current_value_eur || 0) / totalValue) * 100 : 0

                    return (
                      <TableRow key={h.id} className="hover:bg-slate-50 transition-colors">
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <CompanyLogo
                              ticker={h.ticker}
                              name={h.asset_name}
                              isin={h.isin}
                              className="h-8 w-8 rounded-lg"
                            />
                            <div className="flex flex-col min-w-0">
                              <span className="font-bold text-slate-900 text-sm truncate max-w-[260px]" title={h.asset_name || h.ticker}>
                                {h.asset_name || h.ticker}
                              </span>
                              <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono mt-0.5">
                                <span className="font-medium text-slate-400">{h.ticker}</span>
                                {h.isin && (
                                  <>
                                    <span className="text-slate-300">•</span>
                                    <span className="text-slate-400 text-[11px]">{h.isin}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </TableCell>

                        <TableCell>
                          {h.is_etf || h.etf_profile_id ? (
                            <Badge variant="secondary" className="font-normal text-xs">
                              {h.etf_profile_id ? "ETF (décomposé)" : "ETF"}
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="font-normal text-xs text-slate-600">
                              Action
                            </Badge>
                          )}
                        </TableCell>

                        <TableCell className="text-right font-mono text-sm font-medium">
                          {h.quantity}
                        </TableCell>

                        {!hideHoldingValues && (
                          <>
                          <TableCell className="text-right font-mono text-sm">
                            {editingCostId === h.id ? (
                              <div className="flex items-center justify-end gap-1">
                                <Input
                                  autoFocus
                                  type="text"
                                  inputMode="decimal"
                                  value={costDraft}
                                  onChange={(e) => setCostDraft(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter") saveCost(h)
                                    if (e.key === "Escape") setEditingCostId(null)
                                  }}
                                  className="h-7 w-24 text-right font-mono text-xs"
                                  placeholder={`PRU (${h.currency})`}
                                />
                                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-emerald-600" onClick={() => saveCost(h)} title="Enregistrer">
                                  <Check className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-slate-400" onClick={() => setEditingCostId(null)} title="Annuler">
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => startEditCost(h)}
                                className="group inline-flex items-center gap-1.5 hover:text-slate-900"
                                title="Modifier le PRU"
                              >
                                {h.buy_price_avg ? (
                                  <span className="text-slate-700">{h.buy_price_avg.toFixed(2)} {h.currency}</span>
                                ) : (
                                  <span className="text-amber-600 italic text-xs">à renseigner</span>
                                )}
                                <Pencil className="h-3 w-3 text-slate-300 group-hover:text-slate-600" />
                              </button>
                            )}
                          </TableCell>

                          <TableCell className="text-right font-mono text-sm">
                            {h.current_price ? (
                              <div className="flex flex-col items-end">
                                <span className="text-slate-900 font-medium">
                                  {formatCurrency(h.current_price_eur || h.current_price)}
                                </span>
                                {h.currency && h.currency !== "EUR" && (
                                  <span className="text-[10px] text-slate-400 font-normal">
                                    ({h.current_price.toFixed(2)} {h.quote_currency || h.currency})
                                  </span>
                                )}
                                {h.price_date && (
                                  <span
                                    className={cn("text-[10px] font-normal", h.price_stale ? "text-amber-600" : "text-slate-400")}
                                    title={h.price_stale ? "Cours non rafraîchi : dernier cours connu" : "Cours du marché"}
                                  >
                                    {h.price_stale ? "⚠ " : ""}{new Date(h.price_date).toLocaleDateString("fr-FR")}
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-slate-400 italic text-xs">-</span>
                            )}
                          </TableCell>

                          <TableCell className="text-right font-mono text-sm text-slate-600">
                            {h.total_invested_eur != null ? (
                              <span className="amount-blur">{formatCurrency(h.total_invested_eur)}</span>
                            ) : (
                              <span className="text-slate-400 italic text-xs">-</span>
                            )}
                          </TableCell>

                          <TableCell className="text-right font-mono font-bold text-sm text-slate-900">
                            <span className="amount-blur">{formatCurrency(h.current_value_eur || 0)}</span>
                          </TableCell>

                          <TableCell className="text-right font-mono text-sm font-semibold">
                            {h.gain_eur !== undefined && h.gain_eur !== null ? (
                              <div className="flex flex-col items-end">
                                <span className={`amount-blur ${h.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                  {h.gain_eur >= 0 ? "+" : ""}{formatCurrency(h.gain_eur)}
                                </span>
                                <span className={`text-[11px] font-medium ${h.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                  ({h.gain_eur >= 0 ? "+" : ""}{h.gain_pct}%)
                                </span>
                              </div>
                            ) : (
                              <span className="text-slate-400 italic text-xs">-</span>
                            )}
                          </TableCell>

                          <TableCell className="text-right font-mono text-sm">
                            {(h.dividends_received_eur ?? 0) > 0 ? (
                              <div className="flex flex-col items-end">
                                <span className="amount-blur font-semibold text-slate-900">{formatCurrency(h.dividends_received_eur!)}</span>
                                <span className="text-[10px] text-slate-400 font-normal amount-blur">
                                  {formatCurrency(h.dividends_12m_eur ?? 0)} sur 12 mois
                                </span>
                              </div>
                            ) : (
                              <span className="text-slate-400 italic text-xs">-</span>
                            )}
                          </TableCell>

                          <TableCell className="text-right font-mono text-sm font-semibold">
                            {h.total_return_eur !== undefined && h.total_return_eur !== null ? (
                              <div className="flex flex-col items-end">
                                <span className={`amount-blur ${h.total_return_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                  {h.total_return_eur >= 0 ? "+" : ""}{formatCurrency(h.total_return_eur)}
                                </span>
                                <span className={`text-[11px] font-medium ${h.total_return_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                  ({h.total_return_eur >= 0 ? "+" : ""}{h.total_return_pct}%)
                                </span>
                              </div>
                            ) : (
                              <span className="text-slate-400 italic text-xs">-</span>
                            )}
                          </TableCell>

                          <TableCell className="text-right font-mono text-xs text-slate-500 font-medium">
                            {weightPct.toFixed(1)}%
                          </TableCell>
                          </>
                        )}

                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {onAddDividend && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-slate-500 hover:text-emerald-600"
                                onClick={() => onAddDividend(h)}
                                title="Saisir un dividende"
                              >
                                <Coins className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              className={cn("h-8 w-8 p-0", h.pays_dividends ? "text-emerald-600 hover:text-emerald-700" : "text-slate-300 hover:text-slate-600")}
                              onClick={() => handleTogglePaysDividends(h)}
                              title={h.pays_dividends ? "Titre distribuant : cliquer pour désactiver le rappel" : "Marquer comme titre distribuant (rappel de dividende)"}
                            >
                              <CalendarCheck className="h-4 w-4" />
                            </Button>
                            {!h.etf_profile_id && (h.is_etf || h.ticker.startsWith("0P")) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-slate-500 hover:text-slate-900"
                                onClick={() => handleDecompose(h)}
                                disabled={decomposingId === h.id}
                                title="Décomposer en ligne"
                              >
                                <Globe className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-slate-400 hover:text-rose-600"
                              onClick={() => handleDelete(h.id, h.asset_name)}
                              title="Supprimer la position"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <CostEstimateDialog
        open={costEstimateOpen}
        onOpenChange={setCostEstimateOpen}
        accountId={accountId}
        onApplied={onRefresh}
      />

      <PointZeroModal
        open={pointZeroOpen}
        onOpenChange={setPointZeroOpen}
        accountId={accountId}
        accountName={accountName}
        onBaselineSaved={onRefresh}
      />
    </>
  )
}
