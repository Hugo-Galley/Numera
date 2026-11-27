import type { ApiResponse } from "@/lib/api/types"
import { CompositionField, CompositionSource } from "@/types/diversity"

export const COMPOSITION_FIELDS: { key: CompositionField }[] = [
  { key: "sectors" },
  { key: "top_holdings" },
  { key: "countries" },
]

export const SOURCE_LABELS: Record<CompositionSource, { className: string }> = {
  ishares: { className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  amundi: { className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  spdr: { className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  justetf: { className: "bg-amber-50 text-amber-700 border-amber-200" },
  yahoo: { className: "bg-amber-50 text-amber-700 border-amber-200" },
  manual: { className: "bg-slate-100 text-slate-700 border-slate-200" },
}


/** Types du contrat de l'API pour la page Investissements. */
export type InvestmentsAllocation = ApiResponse<"/analytics/investments-allocation", "get">
export type AdvancedAllocation = ApiResponse<"/analytics/investments-allocation-advanced", "get">
