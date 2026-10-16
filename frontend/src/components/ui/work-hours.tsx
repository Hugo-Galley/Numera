import { Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { useWorkTime } from "@/providers/WorkTimeProvider"

/** Durée de travail lisible : minutes, heures puis jours de travail. */
export function formatWorkDuration(hours: number, hoursPerDay: number): string {
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min`
  if (hours < hoursPerDay * 2) {
    const h = Math.floor(hours)
    const min = Math.round((hours - h) * 60)
    if (min === 60) return `${h + 1} h`
    return min > 0 ? `${h} h ${String(min).padStart(2, "0")}` : `${h} h`
  }
  const days = hours / hoursPerDay
  return `${days.toLocaleString("fr-FR", { maximumFractionDigits: days < 10 ? 1 : 0 })} j`
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
      title={`Au taux de ${workTime.hourly_rate.toLocaleString("fr-FR")} €/h net`}
    >
      {showIcon && <Clock className="h-3 w-3" />}≈ {label} de travail
    </span>
  )
}
