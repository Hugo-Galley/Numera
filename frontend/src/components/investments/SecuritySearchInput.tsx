import React, { useState, useEffect, useRef } from "react"
import { api } from "@/lib/api"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Search, CheckCircle2, AlertCircle, RefreshCw, X } from "lucide-react"

export interface SelectedAsset {
  symbol: string
  name: string
  isin?: string
  type?: string
  currency?: string
  price?: number
  price_eur?: number
  etf_profile_id?: number
}

interface SecuritySearchInputProps {
  ticker: string
  isin?: string
  name?: string
  unitPrice?: string
  onSelectAsset: (asset: SelectedAsset) => void
  onChangeTicker: (ticker: string) => void
  onChangeIsin?: (isin: string) => void
  onChangeName?: (name: string) => void
  className?: string
}

export function SecuritySearchInput({
  ticker,
  isin,
  name,
  unitPrice,
  onSelectAsset,
  onChangeTicker,
  onChangeIsin,
  onChangeName,
  className = "",
}: SecuritySearchInputProps) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  // Validation state
  const [isValidating, setIsValidating] = useState(false)
  const [validationInfo, setValidationInfo] = useState<{
    valid: boolean
    name?: string
    symbol?: string
    isin?: string
    price?: number
    price_eur?: number
    currency?: string
    type?: string
  } | null>(null)

  const dropdownRef = useRef<HTMLDivElement>(null)

  // Debounced search on query change
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults([])
      setIsOpen(false)
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const res = await api.get<any[]>(`/market/search?q=${encodeURIComponent(query)}`)
        setResults(res || [])
        setIsOpen(true)
      } catch (err) {
        console.error("Market search error:", err)
      } finally {
        setIsSearching(false)
      }
    }, 280)

    return () => clearTimeout(timer)
  }, [query])

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Auto-validate ticker or ISIN when ticker or isin changes
  useEffect(() => {
    const symbolToValidate = ticker?.trim() || isin?.trim()
    if (!symbolToValidate || symbolToValidate.length < 2) {
      setValidationInfo(null)
      return
    }

    let isMounted = true
    const timer = setTimeout(async () => {
      setIsValidating(true)
      try {
        const res = await api.get<any>(`/market/validate?symbol_or_isin=${encodeURIComponent(symbolToValidate)}`)
        if (isMounted) {
          setValidationInfo(res)
        }
      } catch (err) {
        if (isMounted) {
          setValidationInfo({ valid: false, symbol: symbolToValidate })
        }
      } finally {
        if (isMounted) {
          setIsValidating(false)
        }
      }
    }, 400)

    return () => {
      isMounted = false
      clearTimeout(timer)
    }
  }, [ticker, isin])

  const handleSelect = (asset: any) => {
    setIsOpen(false)
    setQuery("")
    onSelectAsset({
      symbol: asset.symbol,
      name: asset.name,
      isin: asset.isin,
      type: asset.type,
      currency: asset.currency,
      price: asset.price,
      price_eur: asset.price_eur,
      etf_profile_id: asset.etf_profile_id,
    })
  }

  return (
    <div className={`space-y-3 ${className}`} ref={dropdownRef}>
      {/* 1. Main Autocomplete Search Bar */}
      <div className="relative">
        <Label htmlFor="asset-search" className="text-xs font-semibold text-slate-700 flex items-center justify-between">
          <span>Recherche par Titre, Ticker ou ISIN</span>
          {isSearching && (
            <span className="flex items-center gap-1 text-[11px] text-slate-400 font-normal">
              <RefreshCw className="h-3 w-3 animate-spin" /> Recherche...
            </span>
          )}
        </Label>
        <div className="relative mt-1">
          <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
          <Input
            id="asset-search"
            placeholder="Ex: Apple, AAPL, Amundi World, CW8.PA, FR0010315770..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => {
              if (results.length > 0) setIsOpen(true)
            }}
            className="pl-9 pr-8 bg-white border-slate-200 text-xs shadow-2xs"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("")
                setResults([])
                setIsOpen(false)
              }}
              className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Dropdown Results */}
        {isOpen && results.length > 0 && (
          <div className="absolute z-50 w-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl max-h-60 overflow-y-auto divide-y divide-slate-100">
            {results.map((asset, idx) => (
              <div
                key={idx}
                className="p-2.5 hover:bg-slate-50 cursor-pointer flex items-center justify-between transition-colors text-xs"
                onClick={() => handleSelect(asset)}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <CompanyLogo
                    ticker={asset.symbol}
                    name={asset.name}
                    className="h-7 w-7 rounded-md shrink-0 shadow-2xs"
                  />
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-slate-900">{asset.symbol}</span>
                      {asset.isin && (
                        <span className="text-[10px] text-slate-400 font-mono">({asset.isin})</span>
                      )}
                    </div>
                    <p className="text-slate-500 text-[11px] truncate max-w-[260px]">{asset.name}</p>
                  </div>
                </div>
                <div className="text-right shrink-0 flex flex-col items-end gap-0.5">
                  <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4">
                    {asset.type === "ETF" ? "ETF" : "Action"}
                  </Badge>
                  {asset.exchange && (
                    <span className="text-[10px] text-slate-400 uppercase">{asset.exchange}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Direct Ticker & ISIN Inputs */}
      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-1">
          <Label htmlFor="sec-ticker" className="text-xs text-slate-500 font-medium">
            Ticker / Code
          </Label>
          <div className="relative">
            <Input
              id="sec-ticker"
              placeholder="Ex: CW8.PA"
              value={ticker}
              onChange={(e) => onChangeTicker(e.target.value.toUpperCase())}
              className="bg-white uppercase font-mono text-xs pr-7 border-slate-200"
            />
            {ticker && (
              <div className="absolute right-2 top-2">
                <CompanyLogo ticker={ticker} name={name} className="h-4 w-4 rounded-xs shrink-0" />
              </div>
            )}
          </div>
        </div>

        <div className="grid gap-1">
          <Label htmlFor="sec-isin" className="text-xs text-slate-500 font-medium">
            Code ISIN
          </Label>
          <Input
            id="sec-isin"
            placeholder="Ex: FR0010315770"
            value={isin || ""}
            onChange={(e) => onChangeIsin && onChangeIsin(e.target.value.toUpperCase())}
            className="bg-white uppercase font-mono text-xs border-slate-200"
          />
        </div>
      </div>

      {/* 3. Live Verification Status ("Pour savoir si c'est ok ou pas") */}
      {(ticker || isin) && (
        <div className="mt-1">
          {isValidating ? (
            <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 text-xs">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-400" />
              <span>Vérification de l'actif sur les marchés...</span>
            </div>
          ) : validationInfo?.valid ? (
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-200 text-xs">
              <div className="flex items-center gap-2.5 min-w-0">
                <CompanyLogo
                  ticker={validationInfo.symbol || ticker}
                  name={validationInfo.name || name}
                  className="h-6 w-6 rounded-md shadow-2xs shrink-0"
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span className="font-bold text-emerald-900 truncate">
                      {validationInfo.name || validationInfo.symbol}
                    </span>
                    <Badge className="bg-emerald-600 hover:bg-emerald-600 text-white text-[9px] px-1 py-0 h-4">
                      Reconnu
                    </Badge>
                  </div>
                  <div className="text-[11px] text-emerald-700/80 flex items-center gap-2 mt-0.5">
                    <span className="font-mono font-medium">{validationInfo.symbol}</span>
                    {validationInfo.price_eur != null && (
                      <>
                        <span>•</span>
                        <span>Cours : {validationInfo.price_eur.toFixed(2)} €</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-amber-50/60 border border-amber-200/80 text-xs text-amber-900">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />
                <span>
                  Actif non coté en direct (titre personnalisé ou hors marché). La saisie manuelle est conservée.
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
