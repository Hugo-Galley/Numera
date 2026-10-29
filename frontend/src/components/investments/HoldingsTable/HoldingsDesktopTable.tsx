import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CalendarCheck, Check, Coins, Globe, Pencil, Trash2, X } from "lucide-react"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn, formatCurrency, formatRate } from "@/lib/utils"
import type { HoldingsTableCtx } from "./useHoldingsTable"

/** Tableau des positions (bureau). */
export function HoldingsDesktopTable({ ctx }: { ctx: HoldingsTableCtx }) {
  const { costDraft, decomposingId, editingCostId, filteredHoldings, handleDecompose, handleDelete, handleTogglePaysDividends, hideHoldingValues, onAddDividend, saveCost, setCostDraft, setEditingCostId, startEditCost, totalValue } = ctx
  return (
    <>
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
                          ({formatRate(h.gain_pct, 2, true)})
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
                          ({formatRate(h.total_return_pct, 2, true)})
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-400 italic text-xs">-</span>
                    )}
                  </TableCell>

                  <TableCell className="text-right font-mono text-xs text-slate-500 font-medium">
                    {formatRate(weightPct, 1)}
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
    </>
  )
}
