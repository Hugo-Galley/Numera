import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { appLocale } from "@/i18n/locale"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { CompositionSource } from "@/types/diversity"
import type { EtfSheet } from "./types"

const REPLICATIONS = ["physical", "synthetic", "unknown"] as const

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-sm font-semibold text-slate-900 wrap-break-word">{children}</dd>
    </div>
  )
}

/** Carte d'identité du fonds : ce qu'il est, d'où vient sa composition et ce que tu y détiens. */
export function Identity({ sheet }: { sheet: EtfSheet }) {
  const { t } = useTranslation("etfSheet")
  const { t: tInvestments } = useTranslation("investments")
  const { profile } = sheet
  const provider = sheet.provider ? tInvestments(`misc.sources.${sheet.provider as CompositionSource}`) : null
  const replication = REPLICATIONS.find((r) => r === profile.replication) ?? "unknown"
  // Date seule, sans heure : lue en heure locale pour ne pas reculer d'un jour
  const asOf = sheet.composition_as_of ? new Date(`${sheet.composition_as_of}T00:00:00`).toLocaleDateString(appLocale()) : null
  const origin = provider && (asOf
    ? tInvestments("compositionOrigin.asOf", { provider, date: asOf })
    : tInvestments("compositionOrigin.source", { provider }))
  const unavailable = replication === "synthetic" && !sheet.exposure_profile_id && Object.keys(profile.composition_sources ?? {}).length === 0

  return (
    <Card className="shadow-xs">
      <CardContent className="space-y-4 p-4 md:p-5">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 lg:grid-cols-4">
          <Fact label={t("identity.isin")}>{profile.isin || "—"}</Fact>
          <Fact label={t("identity.ticker")}>{profile.ticker}</Fact>
          <Fact label={t("identity.replication")}>{t(`identity.replications.${replication}`)}</Fact>
          <Fact label={t("identity.index")}>{profile.index_name || "—"}</Fact>
        </dl>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          {origin && <Badge variant="outline" className="shadow-none">{origin}</Badge>}
          {!!sheet.coverage_pct && (
            <span data-privacy-ignore>
              {sheet.lines_count
                ? tInvestments("compositionOrigin.lines", { count: sheet.lines_count, lines: sheet.lines_count.toLocaleString(appLocale()), pct: formatRate(sheet.coverage_pct, 1) })
                : t("identity.coverage", { pct: formatRate(sheet.coverage_pct, 0) })}
            </span>
          )}
        </div>
        {sheet.exposure_profile_name && (
          <p className="text-sm text-slate-600">
            {t("identity.syntheticVia", { index: profile.index_name ?? "—", reference: sheet.exposure_profile_name })}
          </p>
        )}
        {unavailable && <p className="text-sm text-amber-700">{tInvestments("compositionOrigin.syntheticUnknown")}</p>}
        {sheet.held_value_eur > 0 && (
          <p className="text-sm font-semibold text-slate-900">
            <span className="amount-blur">{t("identity.held", { amount: formatCurrency(sheet.held_value_eur) })}</span>
          </p>
        )}
      </CardContent>
    </Card>
  )
}
