import { useTranslation } from "react-i18next"
import { AlertTriangle, Layers } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { DiversityScannerResponse, MarketDimensionKey } from "@/types/diversity"
import { formatRate } from "@/lib/utils"
import { BlocksList } from "./BlocksList"
import { MarketGapTable } from "./MarketGapTable"
import { PicksList } from "./PicksList"
import { ReferenceSelect, type ReferenceCandidate } from "./ReferenceSelect"
import { formatDecimal } from "./format"

const DIMENSIONS: MarketDimensionKey[] = ["companies", "sectors", "countries"]

/** Candidats de référence : les fonds détenus (premier ticker de chaque profil), puis la référence en cours. */
function referenceCandidates(data: DiversityScannerResponse): ReferenceCandidate[] {
  const candidates = new Map<string, ReferenceCandidate>()
  for (const etf of data.etf_compositions ?? []) {
    const ticker = etf.tickers[0]
    if (ticker && !candidates.has(ticker)) candidates.set(ticker, { ticker, name: etf.profile_name })
  }
  const market = data.market
  if (market?.ticker && !candidates.has(market.ticker)) candidates.set(market.ticker, { ticker: market.ticker, name: market.name })
  return [...candidates.values()]
}

/**
 * Concentration du portefeuille : paris indépendants, écart au marché par dimension, blocs de lignes corrélées
 * et stock picking redondant. Tous les chiffres viennent du scanner de diversification (backend).
 */
export function Concentration({ data, onReferenceChange }: { data: DiversityScannerResponse; onReferenceChange: () => void }) {
  const { t } = useTranslation("investments")
  const { concentration, market, coverage } = data
  // Réponse d'un backend antérieur au modèle de sur-exposition : rien à montrer
  if (!concentration && market === undefined) return null

  return (
    <Card data-testid="concentration">
      <CardHeader className="gap-3 md:flex md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Layers className="h-5 w-5 text-slate-700" />{t("concentration.title")}
          </CardTitle>
          <CardDescription>{market ? t("concentration.subtitle", { name: market.name }) : t("concentration.subtitleNoMarket")}</CardDescription>
        </div>
        <ReferenceSelect current={market?.ticker ?? null} candidates={referenceCandidates(data)} onChange={onReferenceChange} />
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {concentration && (
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="text-2xl font-black tabular-nums">{formatDecimal(concentration.effective_bets)}</p>
              <p className="text-xs text-slate-500">
                {t("investmentsKpis.effectiveBets", { bets: formatDecimal(concentration.effective_bets), count: concentration.exposures_count })}
              </p>
            </div>
          )}
          {market && DIMENSIONS.map((d) => (
            <div key={d} className="rounded-lg border border-slate-200 p-3">
              <p className="text-2xl font-black tabular-nums">{formatRate(market[d]?.active_share_pct, 0)}</p>
              <p className="text-xs text-slate-500">{t("concentration.activeShare")} · {t(`concentration.dimensions.${d}`)}</p>
            </div>
          ))}
        </div>

        {market ? (
          <MarketGapTable market={market} />
        ) : (
          <p className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-sm text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{t("concentration.noMarket")}
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <BlocksList blocks={concentration?.blocks ?? []} />
          <PicksList picks={data.stock_picking ?? []} />
        </div>

        {coverage && (
          <p className="text-xs text-slate-500">
            {t("concentration.coverage", { composition: formatRate(coverage.composition_pct, 0), prices: formatRate(coverage.with_prices_pct, 0) })}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
