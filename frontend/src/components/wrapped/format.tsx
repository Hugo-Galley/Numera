import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale, percentSuffix } from "@/i18n/locale"
import { ArrowDownRight, ArrowUpRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatWorkDuration } from "@/components/ui/work-hours"

/** Nom du mois en minuscules en français (« juillet »), « July » en anglais (milieu de phrase). */
export function monthName(month: number): string {
  return new Date(2000, month - 1, 1).toLocaleDateString(appLocale(), { month: "long" })
}

export function monthShort(month: number): string {
  return new Date(2000, month - 1, 1).toLocaleDateString(appLocale(), { month: "short" })
}

export function hoursLabel(hours: number | null | undefined, hoursPerDay: number): string | null {
  return hours ? i18n.t("format.ofWork", { ns: "wrapped", duration: formatWorkDuration(hours, hoursPerDay) }) : null
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
  const { t } = useTranslation("wrapped")
  if (value === null || value === undefined || Math.abs(value) < 0.05) return null
  const up = value > 0
  const good = up === higherIsBetter
  const Icon = up ? ArrowUpRight : ArrowDownRight
  const formatted = `${up ? "+" : ""}${value.toLocaleString(appLocale(), { maximumFractionDigits: 1 })}${unit === "%" ? percentSuffix() : " pts"}`
  return (
    <span className={cn("inline-flex items-center gap-1 text-sm font-semibold", good ? "text-emerald-500" : "text-rose-500", className)}>
      <Icon className="h-4 w-4" />
      {formatted} <span className="font-normal opacity-70">{t("format.vs", { year: vsYear })}</span>
    </span>
  )
}
