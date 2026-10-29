import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CalendarCheck, Check, Coins, Globe, Pencil, Trash2, X } from "lucide-react"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Input } from "@/components/ui/input"
import { cn, formatCurrency, formatRate } from "@/lib/utils"
import type { HoldingsTableCtx } from "./useHoldingsTable"

/** Positions en cartes (mobile). */
export function HoldingsMobileList({ ctx }: { ctx: HoldingsTableCtx }) {
  const { costDraft, decomposingId, editingCostId, filteredHoldings, handleDecompose, handleDelete, handleTogglePaysDividends, hideHoldingValues, onAddDividend, saveCost, setCostDraft, setEditingCostId, startEditCost, totalValue } = ctx
  return (
    <>
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
                        <div className="text-xs">({formatRate(h.gain_pct, 2, true)})</div>
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
                      <dd className="font-mono text-sm font-medium tabular-nums">{formatRate(weightPct, 1)}</dd>
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
                          <span className="text-xs">({formatRate(h.total_return_pct, 2, true)})</span>
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
    </>
  )
}
