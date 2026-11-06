import { CompositionField, CompositionSource } from "@/types/diversity"

export const COMPOSITION_FIELDS: { key: CompositionField }[] = [
  { key: "sectors" },
  { key: "top_holdings" },
  { key: "countries" },
]

export const SOURCE_LABELS: Record<CompositionSource, { className: string }> = {
  yahoo: { className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  preset: { className: "bg-amber-50 text-amber-700 border-amber-200" },
  manual: { className: "bg-slate-100 text-slate-700 border-slate-200" },
}

// Monochrome, mais chaque teinte reste lisible sur fond blanc (les gris très clairs disparaissaient)
export const COLORS = ["#0f172a", "#334155", "#475569", "#64748b", "#7c8ba1", "#94a3b8", "#b6c0cc"]
