import { useEffect, useRef, useState } from "react"
import { Globe, Loader2, X } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { Input } from "@/components/ui/input"
import { logoUrl } from "@/components/ui/CompanyLogo"

type Suggestion = { ref: string; title: string; hex: string }

interface LogoPickerProps {
  value: string | null
  onChange: (ref: string | null) => void
  /** Texte (ex. nom de la récurrence) utilisé pour suggérer des logos quand le champ est vide. */
  suggestFor?: string
}

const LOOKS_LIKE_DOMAIN = /^(https?:\/\/)?([a-z0-9-]+\.)+[a-z]{2,}(\/.*)?$/i

function LogoChip({ ref_, label }: { ref_: string; label: string }) {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-md border border-slate-100 bg-white">
      <img src={logoUrl(ref_)} alt={label} className="h-full w-full object-contain p-1" />
    </span>
  )
}

export function LogoPicker({ value, onChange, suggestFor }: LogoPickerProps) {
  const [query, setQuery] = useState("")
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [fetchingDomain, setFetchingDomain] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)

  const effectiveQuery = (query.trim() || suggestFor?.trim() || "").slice(0, 60)
  const isDomain = LOOKS_LIKE_DOMAIN.test(query.trim())

  useEffect(() => {
    if (!open || !effectiveQuery || LOOKS_LIKE_DOMAIN.test(effectiveQuery)) {
      setResults([])
      return
    }
    let cancelled = false
    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const data = await api.get<Suggestion[]>(`/logos/search?q=${encodeURIComponent(effectiveQuery)}`)
        if (!cancelled) setResults(data)
      } catch {
        if (!cancelled) setResults([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 250)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [effectiveQuery, open])

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onDown)
    return () => document.removeEventListener("mousedown", onDown)
  }, [])

  const select = (ref: string | null) => {
    onChange(ref)
    setQuery("")
    setOpen(false)
  }

  const useDomain = async () => {
    setFetchingDomain(true)
    try {
      const res = await api.post<{ ref: string }>("/logos/from-domain", { domain: query.trim() })
      select(res.ref)
    } catch {
      toast.error("Aucun logo trouvé pour ce domaine")
    } finally {
      setFetchingDomain(false)
    }
  }

  return (
    <div ref={boxRef} className="relative">
      {value && (
        <div className="mb-2 flex items-center gap-2">
          <LogoChip ref_={value} label="Logo sélectionné" />
          <span className="text-xs text-slate-500">Logo sélectionné</span>
          <button
            type="button"
            onClick={() => select(null)}
            className="ml-auto flex items-center gap-1 text-xs text-slate-500 hover:text-rose-600"
          >
            <X className="h-3 w-3" /> Retirer
          </button>
        </div>
      )}
      <Input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        placeholder="Entreprise ou produit (Claude, YouTube…) ou site (navigo.fr)"
        autoComplete="off"
      />
      {open && (
        <div className="absolute z-50 mt-1 max-h-64 w-full overflow-y-auto rounded-md border bg-white p-1 shadow-md">
          {loading && (
            <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-slate-400">
              <Loader2 className="h-3 w-3 animate-spin" /> Recherche…
            </div>
          )}
          {results.map((r) => (
            <button
              key={r.ref}
              type="button"
              onClick={() => select(r.ref)}
              className="flex w-full items-center gap-3 rounded px-2 py-1.5 text-left text-sm hover:bg-slate-100"
            >
              <LogoChip ref_={r.ref} label={r.title} />
              <span className="truncate font-medium text-slate-800">{r.title}</span>
            </button>
          ))}
          {!loading && effectiveQuery && !isDomain && results.length === 0 && (
            <p className="px-2 py-1.5 text-xs text-slate-400">Aucun logo pour « {effectiveQuery} ».</p>
          )}
          {isDomain ? (
            <button
              type="button"
              onClick={useDomain}
              disabled={fetchingDomain}
              className="flex w-full items-center gap-3 rounded px-2 py-1.5 text-left text-sm hover:bg-slate-100 disabled:opacity-60"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-slate-50">
                {fetchingDomain ? <Loader2 className="h-4 w-4 animate-spin" /> : <Globe className="h-4 w-4 text-slate-500" />}
              </span>
              <span className="truncate">Utiliser le logo de <b>{query.trim()}</b></span>
            </button>
          ) : (
            <p className="px-2 py-1.5 text-[11px] text-slate-400">Entreprise absente ? Tapez son site (ex. navigo.fr).</p>
          )}
        </div>
      )}
    </div>
  )
}
