import { Button } from "@/components/ui/button"
import { Calculator, Layers, Search, SlidersHorizontal, X } from "lucide-react"
import { CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { PerfFilter, TypeFilter } from "./types"
import type { HoldingsTableCtx } from "./useHoldingsTable"

/** En-tête : titre, actions (point zéro, estimation des frais) et barre de filtres. */
export function HoldingsHeader({ ctx }: { ctx: HoldingsTableCtx }) {
  const { hasActiveFilters, hideHoldingValues, holdings, perfFilter, resetFilters, search, setCostEstimateOpen, setPerfFilter, setPointZeroOpen, setSearch, setTypeFilter, typeFilter } = ctx
  return (
    <>
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
    </>
  )
}
