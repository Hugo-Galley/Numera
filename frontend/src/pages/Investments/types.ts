import { CompositionField, CompositionSource } from "@/types/diversity"

export const COMPOSITION_FIELDS: { key: CompositionField; label: string }[] = [
  { key: "sectors", label: "Secteurs" },
  { key: "top_holdings", label: "Top 10" },
  { key: "countries", label: "Pays" },
]

export const SOURCE_LABELS: Record<CompositionSource, { label: string; className: string }> = {
  yahoo: { label: "Yahoo", className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  preset: { label: "Préréglage", className: "bg-amber-50 text-amber-700 border-amber-200" },
  manual: { label: "Saisie", className: "bg-slate-100 text-slate-700 border-slate-200" },
}

// Monochrome, mais chaque teinte reste lisible sur fond blanc (les gris très clairs disparaissaient)
export const COLORS = ["#0f172a", "#334155", "#475569", "#64748b", "#7c8ba1", "#94a3b8", "#b6c0cc"]
