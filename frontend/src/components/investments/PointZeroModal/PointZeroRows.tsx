import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Input } from "@/components/ui/input"
import { Layers, Trash2 } from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import type { PointZeroModalCtx } from "./usePointZeroModal"

/** Tableau des lignes du point zéro. */
export function PointZeroRows({ ctx }: { ctx: PointZeroModalCtx }) {
  const { handleRemoveRow, handleUpdateRow, loadingSuggestions, rows } = ctx
  return (
    <>
      {/* Table of Rows */}
      <div className="flex-1 min-h-[140px] overflow-y-auto mt-4 border border-slate-200 rounded-lg bg-white">
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
            <div className="hidden md:grid grid-cols-12 gap-2 px-3 py-2 text-xs font-semibold text-slate-500 bg-slate-50/80 border-b border-slate-100">
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
                <div key={idx}>
                {/* Mobile : carte */}
                <div className="space-y-3 p-3 md:hidden">
                  <div className="flex items-start gap-2.5">
                    <CompanyLogo ticker={row.ticker} name={row.asset_name} isin={row.isin} className="h-9 w-9 rounded-md shrink-0 shadow-2xs" />
                    <div className="min-w-0 flex-1">
                      <div className="break-words text-sm font-semibold leading-snug text-slate-900">{row.asset_name || row.ticker}</div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                        <span className="font-mono text-[11px] text-slate-500">{row.ticker}{row.isin ? ` • ${row.isin}` : ""}</span>
                        <Badge variant={row.is_etf ? "secondary" : "outline"} className="px-1.5 py-0 text-[10px] font-normal">{row.is_etf ? "ETF" : "Action"}</Badge>
                        {row.is_suggestion && row.quantity === 0 && (
                          <Badge variant="outline" className="border-amber-200 bg-amber-50 px-1.5 py-0 text-[10px] font-normal text-amber-700">Suggéré</Badge>
                        )}
                      </div>
                    </div>
                    <Button type="button" variant="ghost" size="icon" className="-mr-1 -mt-1 h-10 w-10 shrink-0 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => handleRemoveRow(idx)} aria-label="Retirer cette ligne">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="grid grid-cols-[1fr_6.5rem] items-end gap-3">
                    <div className="min-w-0 text-xs text-slate-500">
                      <div>Cours : <span className="font-mono font-medium text-slate-800">{row.current_price ? `${row.current_price.toFixed(2)} ${row.currency}` : "-"}</span></div>
                      <div className="mt-1">Valeur : <span className="whitespace-nowrap font-mono text-sm font-semibold text-slate-900">{new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(rowVal)}</span></div>
                    </div>
                    <label className="block text-xs text-slate-500">
                      Parts
                      <Input
                        type="number"
                        inputMode="decimal"
                        step="any"
                        min="0"
                        placeholder="0"
                        value={row.quantity || ""}
                        onChange={(e) => handleUpdateRow(idx, "quantity", parseFloat(e.target.value) || 0)}
                        className="mt-1 h-11 bg-white text-right font-mono text-base text-slate-900"
                      />
                    </label>
                  </div>
                </div>
                {/* Bureau : ligne de tableau */}
                <div
                  className="hidden md:grid grid-cols-12 gap-2 px-3 py-2 items-center hover:bg-slate-50/60 transition-colors"
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
                            (~{formatCurrency(row.current_price_eur)})
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">-</span>
                    )}
                  </div>

                  <div className="col-span-2 text-right">
                    <Input
                      type="number" inputMode="decimal"
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
                    <Button aria-label="Supprimer"
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
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
