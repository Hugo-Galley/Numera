import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Input } from "@/components/ui/input"
import { Loader2, Plus, Search, X } from "lucide-react"
import type { PointZeroModalCtx } from "./usePointZeroModal"

/** Recherche d'un titre à ajouter (et création d'un ETF personnalisé). */
export function PointZeroSearch({ ctx }: { ctx: PointZeroModalCtx }) {
  const { handleSelectSearchResult, isSearching, searchQuery, searchResults, setCustomEtfOpen, setPendingEtfSearch, setSearchQuery, setSearchResults, setShowSearchDropdown, showSearchDropdown } = ctx
  return (
    <>
      {/* Search bar */}
      <div className="relative mt-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="ISIN, ticker (CW8.PA) ou nom…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-11 pl-9 pr-10 text-base sm:h-9 sm:pr-8 sm:text-sm bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 shadow-2xs focus-visible:ring-1 focus-visible:ring-slate-400"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("")
                  setSearchResults([])
                  setShowSearchDropdown(false)
                }}
                className="absolute right-0 top-1/2 flex h-11 w-10 -translate-y-1/2 items-center justify-center text-slate-400 hover:text-slate-600 sm:right-2.5 sm:h-auto sm:w-auto sm:p-0.5"
                aria-label="Effacer la recherche"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <Button
            type="button"
            variant="outline"
            className="shrink-0 gap-1.5 text-sm h-10 sm:h-9 sm:text-xs border-slate-200 text-slate-700 hover:bg-slate-50"
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
                    className="flex min-h-12 cursor-pointer flex-col gap-1.5 p-3 text-xs transition-colors hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
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
                        <span className="max-w-[280px] truncate text-xs font-semibold text-slate-900 max-sm:max-w-[60vw]">
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

                    <div className="flex shrink-0 flex-wrap items-center gap-2 pl-[38px] sm:pl-0">
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
    </>
  )
}
