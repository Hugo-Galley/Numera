import i18n from "i18next"
import { appLocale } from "@/i18n/locale"
import { Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { useWorkTime } from "@/providers/WorkTimeProvider"

/** Durée de travail lisible : minutes, heures puis jours de travail. */
export function formatWorkDuration(hours: number, hoursPerDay: number): string {
  if (hours < 1) return i18n.t("workHours.minutes", { ns: "common", n: Math.max(1, Math.round(hours * 60)) })
  if (hours < hoursPerDay * 2) {
    const h = Math.floor(hours)
    const min = Math.round((hours - h) * 60)
    if (min === 60) return i18n.t("workHours.hours", { ns: "common", n: h + 1 })
    return min > 0
      ? i18n.t("workHours.hoursMinutes", { ns: "common", h, min: String(min).padStart(2, "0") })
      : i18n.t("workHours.hours", { ns: "common", n: h })
  }
  const days = hours / hoursPerDay
  return i18n.t("workHours.days", { ns: "common", value: days.toLocaleString(appLocale(), { maximumFractionDigits: days < 10 ? 1 : 0 }) })
}

interface WorkHoursProps {
  /** Montant en euros (le salaire est configuré en EUR). */
  amount: number
  className?: string
  showIcon?: boolean
}

/** « ≈ 3 h 20 de travail » ; rien si le salaire n'est pas configuré. */
export function WorkHours({ amount, className, showIcon = true }: WorkHoursProps) {
  const { workTime } = useWorkTime()
  if (!workTime?.hourly_rate || !amount || amount <= 0) return null
  const label = formatWorkDuration(amount / workTime.hourly_rate, workTime.work_hours_per_day)
  return (
    <span
      className={cn("inline-flex items-center gap-1 text-[10px] font-normal text-slate-400 amount-blur", className)}
      title={i18n.t("workHours.rate", { ns: "common", rate: workTime.hourly_rate.toLocaleString(appLocale()) })}
    >
      {showIcon && <Clock className="h-3 w-3" />}{i18n.t("workHours.approx", { ns: "common", duration: label })}
    </span>
  )
}
