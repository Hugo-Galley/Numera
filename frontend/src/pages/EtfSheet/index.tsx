import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft, Info } from "lucide-react"
import { ErrorState } from "@/components/layout/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Identity } from "./Identity"
import type { DisplayLine } from "./lines"
import { LinesTable } from "./LinesTable"
import type { EtfSheet } from "./types"
import { useEtfSheet } from "./useEtfSheet"
import { Weights } from "./Weights"

/** Toutes les lignes, sinon les principales que la source publie. */
function displayLines(sheet: EtfSheet): DisplayLine[] {
  if (sheet.has_full_list) return sheet.lines.map((line, key) => ({ ...line, key, exposure: line.exposure_eur ?? 0 }))
  return sheet.top_holdings.map((h, key) => ({
    key,
    name: String(h.name ?? ""),
    ticker: typeof h.ticker === "string" ? h.ticker : null,
    isin: typeof h.isin === "string" ? h.isin : null,
    weight: Number(h.weight) || 0,
    exposure: Number(h.exposure_eur) || 0,
  }))
}

function Composition({ sheet }: { sheet: EtfSheet }) {
  const { t } = useTranslation("etfSheet")
  const lines = useMemo(() => displayLines(sheet), [sheet])
  const nothing = lines.length === 0 && sheet.countries.length === 0 && sheet.sectors.length === 0
  const notice = nothing ? t("noComposition") : sheet.has_full_list ? null : t("noFullList")
  return (
    <>
      <Identity sheet={sheet} />
      {notice && (
        <p className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" />
          {notice}
        </p>
      )}
      <Weights countries={sheet.countries} sectors={sheet.sectors} />
      {lines.length > 0 && <LinesTable lines={lines} showExposure={sheet.held_value_eur > 0} />}
    </>
  )
}

/** Fiche d'un ETF : identité du fonds, pays, secteurs et toutes ses sociétés. */
export default function EtfSheetPage() {
  const { t } = useTranslation("etfSheet")
  const { profileId = "" } = useParams()
  const { sheet, error, retry } = useEtfSheet(profileId, t("loadError"))

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <Link to="/investments" className="inline-flex min-h-10 items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          {t("back")}
        </Link>
        {sheet && <h1 className="text-2xl font-black text-slate-900 wrap-break-word">{sheet.profile.name}</h1>}
      </header>
      {error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : !sheet ? (
        <div className="space-y-4" aria-busy="true">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        // `key` : une autre fiche repart d'une recherche et d'un tri neufs
        <Composition key={sheet.profile.id} sheet={sheet} />
      )}
    </div>
  )
}
