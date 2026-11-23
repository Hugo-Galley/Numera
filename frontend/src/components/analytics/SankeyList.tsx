import { useTranslation } from "react-i18next"
import { ChevronRight } from "lucide-react"
import { formatCurrency } from "@/lib/utils"
import { DEFAULT_COLOR, type SankeyData } from "./sankeyLayout"

interface SankeyListProps {
  data: SankeyData | null
  currency?: string
  onCategoryClick?: (categoryId: number, name: string) => void
}

interface Section {
  index: number
  name: string
  total: number
  rows: { index: number; name: string; value: number; color: string; categoryId: number | null }[]
}

/**
 * Lecture du Sankey en liste, pour un écran étroit : une section par nœud qui redistribue de l'argent
 * (sources d'abord, puis les nœuds dans l'ordre du flux), chaque flux sortant en barre proportionnelle.
 * Aucun montant recalculé : ce sont les valeurs des liens renvoyées par l'API.
 */
export function SankeyList({ data, currency = "EUR", onCategoryClick }: SankeyListProps) {
  const { t } = useTranslation("settings")
  if (!data || !data.nodes?.length || !data.links?.length) {
    return (
      <div className="flex h-[120px] items-center justify-center text-slate-400">
        {data ? t("sankeyFlow.pasAssezDeDonneesPour") : t("sankeyFlow.chargementDuDiagramme")}
      </div>
    )
  }

  const n = data.nodes.length
  const links = data.links.filter((l) => l.value > 0 && l.source < n && l.target < n)
  const hasIncoming = new Set(links.map((l) => l.target))
  // Ordre du flux : parcours en largeur depuis les nœuds sans entrée
  const order: number[] = []
  const seen = new Set<number>()
  const queue = data.nodes.map((_, i) => i).filter((i) => !hasIncoming.has(i))
  while (queue.length) {
    const i = queue.shift() as number
    if (seen.has(i)) continue
    seen.add(i)
    order.push(i)
    links.filter((l) => l.source === i).sort((a, b) => b.value - a.value).forEach((l) => queue.push(l.target))
  }

  const sections: Section[] = order
    .map((i) => {
      const out = links.filter((l) => l.source === i).sort((a, b) => b.value - a.value)
      return {
        index: i,
        name: data.nodes[i].name,
        total: out.reduce((s, l) => s + l.value, 0),
        rows: out.map((l) => {
          const node = data.nodes[l.target]
          return {
            index: l.target,
            name: node.name,
            value: l.value,
            color: node.color || l.color || DEFAULT_COLOR,
            categoryId: node.category_id ?? null,
          }
        }),
      }
    })
    .filter((s) => s.rows.length > 0)

  return (
    <div className="space-y-4">
      {sections.map((section) => (
        <section key={section.index} aria-label={section.name} className="space-y-1.5">
          <h3 className="flex items-baseline justify-between gap-2 border-b border-slate-100 pb-1 text-xs font-bold uppercase tracking-wide text-slate-500">
            <span className="min-w-0 break-words">{section.name}</span>
            <span className="shrink-0 whitespace-nowrap tabular-nums text-slate-700">{formatCurrency(section.total, currency)}</span>
          </h3>
          <ul className="space-y-1">
            {section.rows.map((row) => {
              const share = section.total > 0 ? (row.value / section.total) * 100 : 0
              const clickable = row.categoryId != null && !!onCategoryClick
              const content = (
                <>
                  <span className="flex items-center justify-between gap-2 text-sm">
                    <span className="flex min-w-0 items-center gap-2 font-medium text-slate-800">
                      <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: row.color }} />
                      <span className="break-words">{row.name}</span>
                    </span>
                    <span className="flex shrink-0 items-center gap-1 whitespace-nowrap tabular-nums font-semibold text-slate-900">
                      {formatCurrency(row.value, currency)}
                      {clickable && <ChevronRight className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />}
                    </span>
                  </span>
                  <span className="mt-1 block h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <span className="block h-full rounded-full" style={{ width: `${share}%`, backgroundColor: row.color }} />
                  </span>
                </>
              )
              return (
                <li key={`${section.index}-${row.index}`}>
                  {clickable ? (
                    <button
                      type="button"
                      className="block min-h-11 w-full rounded-lg px-1 py-1.5 text-left active:bg-slate-50"
                      onClick={() => onCategoryClick?.(row.categoryId as number, row.name)}
                    >
                      {content}
                    </button>
                  ) : (
                    <div className="px-1 py-1.5">{content}</div>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}
