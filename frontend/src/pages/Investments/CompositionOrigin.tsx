import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { formatRate } from "@/lib/utils"
import type { CompositionSource, EtfCompositionInfo } from "@/types/diversity"

/** Source et date de la composition utilisée, exposition d'un synthétique, part du fonds décrite. */
export function CompositionOrigin({ composition: c }: { composition: EtfCompositionInfo }) {
  const { t } = useTranslation("investments")
  const synthetic = c.replication === "synthetic"
  // Indice inconnu : sans saisie manuelle, il n'y a aucune répartition à montrer
  const unavailable = synthetic && !c.exposure_profile_id && Object.keys(c.sources).length === 0
  return (
    <div className="mt-0.5 space-y-0.5 text-xs text-slate-500 wrap-break-word">
      {c.provider && c.composition_as_of && (
        <p>
          {t("compositionOrigin.asOf", {
            provider: t(`misc.sources.${c.provider as CompositionSource}`),
            // Date seule, sans heure : lue en heure locale pour ne pas reculer d'un jour
            date: new Date(`${c.composition_as_of}T00:00:00`).toLocaleDateString(appLocale()),
          })}
        </p>
      )}
      {synthetic && c.exposure_profile_name && (
        <p>{t("compositionOrigin.syntheticVia", { index: c.index_name, reference: c.exposure_profile_name })}</p>
      )}
      {unavailable && <p className="text-amber-700">{t("compositionOrigin.syntheticUnknown")}</p>}
      {!!c.coverage_pct && (
        <p>
          {c.lines_count
            ? t("compositionOrigin.lines", { count: c.lines_count, lines: c.lines_count.toLocaleString(appLocale()), pct: formatRate(c.coverage_pct, 0) })
            : t("compositionOrigin.topTen", { pct: formatRate(c.coverage_pct, 0) })}
        </p>
      )}
    </div>
  )
}
