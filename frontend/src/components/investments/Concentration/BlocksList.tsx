import { useTranslation } from "react-i18next"
import { Link2 } from "lucide-react"
import type { CorrelatedBlock } from "@/types/diversity"
import { formatRate } from "@/lib/utils"
import { formatRho } from "./format"

/** Blocs d'expositions qui bougent ensemble (ρ moyen au-dessus du seuil du modèle). */
export function BlocksList({ blocks }: { blocks: CorrelatedBlock[] }) {
  const { t } = useTranslation("investments")
  return (
    <div className="space-y-2">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <Link2 className="h-4 w-4 text-slate-400" />{t("concentration.blocks.title")}
      </h3>
      {blocks.length === 0 ? (
        <p className="text-sm text-slate-500">{t("concentration.blocks.empty")}</p>
      ) : (
        <ul className="space-y-2">
          {blocks.map((block) => (
            <li key={block.members.join("|")} className="rounded-lg border border-slate-200 p-3 text-sm">
              <p className="font-medium text-slate-900">
                {block.members.join(" + ")} · {t("concentration.blocks.rho", { rho: formatRho(block.mean_rho) })}
              </p>
              <p className="text-xs text-slate-500">{t("concentration.blocks.weight", { pct: formatRate(block.weight_pct, 1) })}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
