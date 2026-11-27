import { Trans, useTranslation } from "react-i18next"
import { Crosshair } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { StockPickingLine } from "@/types/diversity"
import { formatCurrency } from "@/lib/utils"
import { formatRho } from "./format"

/** Actions en direct : part déjà détenue via les fonds et corrélation avec le cœur du portefeuille. */
export function PicksList({ picks }: { picks: StockPickingLine[] }) {
  const { t } = useTranslation("investments")
  return (
    <div className="space-y-2">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <Crosshair className="h-4 w-4 text-slate-400" />{t("concentration.picks.title")}
      </h3>
      {picks.length === 0 ? (
        <p className="text-sm text-slate-500">{t("concentration.picks.empty")}</p>
      ) : (
        <ul className="space-y-2">
          {picks.map((pick) => (
            <li key={pick.key} className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-slate-200 p-3 text-sm">
              <div>
                <p className="font-medium text-slate-900">{pick.name}</p>
                <p className="text-xs text-slate-500">
                  {pick.indirect_value_eur > 0 ? (
                    <Trans t={t} i18nKey="concentration.picks.indirect" values={{ amount: formatCurrency(pick.indirect_value_eur) }} components={{ amount: <span className="amount-blur" /> }} />
                  ) : t("concentration.picks.noIndirect")}
                  {" · "}
                  {pick.correlation_with_core == null
                    ? t("concentration.picks.correlationUnknown")
                    : `${t("concentration.picks.correlation", { rho: formatRho(pick.correlation_with_core) })} (${t(`concentration.picks.source.${pick.source}`)})`}
                </p>
              </div>
              {pick.redundant && <Badge variant="secondary" className="border-amber-200 bg-amber-50 text-amber-700">{t("concentration.picks.redundant")}</Badge>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
