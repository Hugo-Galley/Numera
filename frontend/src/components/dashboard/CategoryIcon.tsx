import { IconComponent } from "@/components/dashboard/IconComponent"
import { cn } from "@/lib/utils"

/**
 * Pastille carrée avec l'icône d'une catégorie.
 * Couleur de catégorie : fond inline et icône blanche. Sans couleur : fond et icône neutres du thème
 * (classes ardoise, inversées en sombre), jamais un hexadécimal clair inline qui resterait blanc en sombre.
 */
export function CategoryIcon({ category, className, iconClassName }: {
  category: { color?: string | null; icon?: string | null } | null | undefined
  className?: string
  iconClassName?: string
}) {
  const color = category?.color || null
  return (
    <span
      aria-hidden="true"
      className={cn("flex shrink-0 items-center justify-center rounded-md", color ? null : "bg-slate-100", className)}
      style={color ? { backgroundColor: color } : undefined}
    >
      <IconComponent name={category?.icon} className={cn(color ? "text-white" : "text-slate-600", iconClassName)} />
    </span>
  )
}
