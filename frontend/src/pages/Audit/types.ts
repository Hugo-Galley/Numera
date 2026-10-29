import { RefreshCw, ShieldCheck, ShoppingBag, Target, Zap } from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import { toInputValue } from "@/lib/dates"

export interface Category {
  id: number
  name: string
  type: string
}

export interface Transaction {
  id: number
  account_id: number
  date: string
  type: string
  merchant: string
  category_id: number | null
  amount: number
  currency: string
  note?: string | null
}

export interface Account {
  id: number
  name: string
  currency: string
}

export interface ActionItem {
  id: string
  type: "audit" | "budget" | "rule" | "subscription"
  severity: "low" | "medium" | "high"
  title: string
  description: string
  action_label?: string | null
  action_url?: string | null
  action_type: "link" | "modal_categorize" | "modal_rule" | "modal_snapshot" | "modal_merchant"
  metadata?: Record<string, any>
  samples: Array<Record<string, any>>
}

export interface ActionCenterData {
  summary: {
    total_actions: number
    high_priority: number
    medium_priority: number
    low_priority: number
    checked_at: string
  }
  actions: ActionItem[]
}

export interface IssueDetails {
  issue_id: string
  transactions?: Transaction[]
  duplicate_groups?: Array<{ key: string; count: number; transactions: Transaction[] }>
  transfer_pairs?: Array<{ sortie: Transaction; entree: Transaction }>
}

// Mêmes mots que les compteurs du haut (« Priorité haute / moyenne », « Suggestions »)
export const severityLabel = {
  high: "Priorité haute",
  medium: "Priorité moyenne",
  low: "Suggestion",
}

export const severityClass = {
  high: "border-rose-200 text-rose-600",
  medium: "border-amber-200 text-amber-600",
  low: "border-slate-200 text-slate-500",
}

export const actionIconClass = {
  high: "text-rose-500",
  medium: "text-amber-500",
  low: "text-slate-400",
}

export const actionTypeIcon = {
  audit: ShieldCheck,
  budget: Target,
  rule: Zap,
  subscription: RefreshCw,
  merchant: ShoppingBag,
}

export const toDateTimeLocal = toInputValue

export function sampleLabel(sample: Record<string, any>) {
  if (sample.sortie && sample.entree) {
    return `${sample.sortie.merchant || "Sortie"} -> ${sample.entree.merchant || "Entree"}`
  }
  if (sample.name) return sample.name
  if (sample.merchant) return sample.merchant
  if (sample.date && sample.amount !== undefined) return `${sample.date} - ${formatCurrency(sample.amount, sample.currency || "EUR")}`
  return JSON.stringify(sample)
}
