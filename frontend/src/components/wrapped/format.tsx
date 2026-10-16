import { ArrowDownRight, ArrowUpRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatWorkDuration } from "@/components/ui/work-hours"

const MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

export function monthName(month: number): string {
  return MONTHS[month - 1] ?? ""
}

const MONTHS_SHORT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

export function monthShort(month: number): string {
  return MONTHS_SHORT[month - 1] ?? ""
}

export function hoursLabel(hours: number | null | undefined, hoursPerDay: number): string | null {
  return hours ? `≈ ${formatWorkDuration(hours, hoursPerDay)} de travail` : null
}

interface DeltaProps {
  /** Variation en % (ou en points avec `unit="pts"`). */
  value: number | null | undefined
  unit?: "%" | "pts"
  /** Une hausse est-elle une bonne nouvelle ? (faux pour les dépenses) */
  higherIsBetter?: boolean
  vsYear: number
  className?: string
}

/** « ↗ +12 % vs 2025 », coloré selon que la variation est favorable. */
export function Delta({ value, unit = "%", higherIsBetter = true, vsYear, className }: DeltaProps) {
  if (value === null || value === undefined || Math.abs(value) < 0.05) return null
  const up = value > 0
  const good = up === higherIsBetter
  const Icon = up ? ArrowUpRight : ArrowDownRight
  const formatted = `${up ? "+" : ""}${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })}${unit === "%" ? " %" : " pts"}`
  return (
    <span className={cn("inline-flex items-center gap-1 text-sm font-semibold", good ? "text-emerald-500" : "text-rose-500", className)}>
      <Icon className="h-4 w-4" />
      {formatted} <span className="font-normal opacity-70">vs {vsYear}</span>
    </span>
  )
}
