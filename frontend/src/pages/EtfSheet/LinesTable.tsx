import { useDeferredValue, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowDown, ArrowUp, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useIsMobile } from "@/hooks/useIsMobile"
import { appLocale } from "@/i18n/locale"
import { countryName } from "@/lib/countries"
import { formatCurrency, formatRate } from "@/lib/utils"
import { searchLines, sortLines, type DisplayLine, type LineSort } from "./lines"

/** Lignes rendues d'un coup : un grand fonds en compte plus de 1 500. */
const PAGE_SIZE = 50
const SORTS: LineSort[] = ["name", "country", "sector", "weight"]

interface LinesProps {
  lines: DisplayLine[]
  /** Valeur détenue du fonds ; 0 : l'exposition n'est pas affichée */
  heldValue: number
}

const identifiers = (line: DisplayLine) => [line.ticker, line.isin].filter(Boolean).join(" · ")

function Exposure({ line, heldValue }: { line: DisplayLine; heldValue: number }) {
  return <span className="amount-blur whitespace-nowrap tabular-nums">{formatCurrency((line.weight / 100) * heldValue)}</span>
}

function DesktopLines({ rows, heldValue, sort, onSort }: { rows: DisplayLine[]; heldValue: number; sort: LineSort; onSort: (s: LineSort) => void }) {
  const { t } = useTranslation("etfSheet")
  const Arrow = sort === "weight" ? ArrowDown : ArrowUp
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {SORTS.map((column) => (
            <TableHead key={column} className={column === "weight" ? "text-right" : ""} aria-label={t(`lines.columns.${column}`)}
              aria-sort={sort === column ? (column === "weight" ? "descending" : "ascending") : undefined}>
              <button type="button" className="inline-flex min-h-10 items-center gap-1 font-semibold hover:text-slate-900" onClick={() => onSort(column)}>
                {t(`lines.columns.${column}`)}
                {sort === column && <Arrow className="h-3 w-3" aria-hidden="true" />}
              </button>
            </TableHead>
          ))}
          {heldValue > 0 && <TableHead className="text-right">{t("lines.columns.exposure")}</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((line) => (
          <TableRow key={line.key}>
            <TableCell className="max-w-[320px]">
              <span className="block truncate font-medium text-slate-900" title={line.name}>{line.name}</span>
              <span className="block truncate text-xs text-slate-500">{identifiers(line)}</span>
            </TableCell>
            <TableCell>{line.country ? countryName(line.country) : "—"}</TableCell>
            <TableCell>{line.sector || "—"}</TableCell>
            <TableCell className="text-right font-semibold tabular-nums">{formatRate(line.weight, 2)}</TableCell>
            {heldValue > 0 && <TableCell className="text-right"><Exposure line={line} heldValue={heldValue} /></TableCell>}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function MobileLines({ rows, heldValue }: { rows: DisplayLine[]; heldValue: number }) {
  const { t } = useTranslation("etfSheet")
  return (
    <ul className="divide-y divide-slate-100">
      {rows.map((line) => (
        <li key={line.key} className="flex items-start justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-slate-900">{line.name}</p>
            <p className="truncate text-xs text-slate-500">{identifiers(line)}</p>
            <p className="text-xs text-slate-500 wrap-break-word">
              {line.country ? countryName(line.country) : "—"} · {line.sector || "—"}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-sm font-semibold text-slate-900 tabular-nums">{formatRate(line.weight, 2)}</p>
            {heldValue > 0 && (
              <p className="text-xs text-slate-500" title={t("lines.columns.exposure")}><Exposure line={line} heldValue={heldValue} /></p>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

/** Toutes les sociétés du fonds : recherche, tri, affichage par paquets de 50. */
export function LinesTable({ lines, heldValue }: LinesProps) {
  const { t } = useTranslation("etfSheet")
  const isMobile = useIsMobile()
  const [query, setQuery] = useState("")
  const [sort, setSort] = useState<LineSort>("weight")
  const [visible, setVisible] = useState(PAGE_SIZE)
  const deferredQuery = useDeferredValue(query)

  const sorted = useMemo(() => sortLines(lines, sort), [lines, sort])
  const found = useMemo(() => searchLines(sorted, deferredQuery), [sorted, deferredQuery])
  const rows = found.slice(0, visible)
  const more = Math.min(PAGE_SIZE, found.length - rows.length)
  const changeSort = (next: LineSort) => { setSort(next); setVisible(PAGE_SIZE) }

  return (
    <Card className="shadow-xs">
      <CardHeader className="flex flex-col gap-3 border-b pb-3 md:flex-row md:items-center md:justify-between">
        {/* Un nombre de lignes n'est pas un montant : le mode confidentialité ne doit pas le masquer */}
        <CardTitle className="text-base" data-privacy-ignore>
          {t("lines.title", { count: found.length, lines: found.length.toLocaleString(appLocale()) })}
        </CardTitle>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative sm:w-72">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <Input className="h-10 pl-9 text-base md:text-sm" value={query} aria-label={t("lines.search")} placeholder={t("lines.searchPlaceholder")}
              onChange={(e) => { setQuery(e.target.value); setVisible(PAGE_SIZE) }} />
          </div>
          {isMobile && (
            <select className="h-10 rounded-md border border-slate-200 bg-white px-3 text-base text-slate-900" aria-label={t("lines.sortBy")}
              value={sort} onChange={(e) => changeSort(e.target.value as LineSort)}>
              {SORTS.map((s) => <option key={s} value={s}>{t(`lines.columns.${s}`)}</option>)}
            </select>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {rows.length === 0
          ? <p className="p-6 text-center text-sm text-slate-500">{t("lines.noMatch")}</p>
          : isMobile
            ? <MobileLines rows={rows} heldValue={heldValue} />
            : <DesktopLines rows={rows} heldValue={heldValue} sort={sort} onSort={changeSort} />}
        {more > 0 && (
          <div className="border-t p-3 text-center">
            <Button variant="outline" className="min-h-10" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
              {t("lines.showMore", { count: more })}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
