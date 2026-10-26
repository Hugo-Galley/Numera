import { useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { format, parseISO } from "date-fns"
import { fr } from "date-fns/locale"
import { ArrowRight, ListFilter, Split } from "lucide-react"

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/layout/ErrorState"
import { readDrilldown, useDrilldown } from "@/hooks/useDrilldown"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"

interface DrilldownTransaction {
  id: number
  account_id: number
  date: string
  merchant: string
  amount: number
  reimbursement_offset?: number
  note: string | null
  category: { id: number; name: string } | null
  merchant_obj?: { name: string } | null
  splits?: { category_id: number | null; amount: number; category?: { name: string } | null }[]
}

interface AccountOption {
  id: number
  name: string
  currency: string
}

const MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

/** Panneau « transactions derrière ce chiffre », ouvert par `useDrilldown().openDrilldown`. */
export function DrilldownSheet() {
  const [searchParams] = useSearchParams()
  const filters = useMemo(() => readDrilldown(searchParams), [searchParams])
  const { closeDrilldown } = useDrilldown()
  const [rows, setRows] = useState<DrilldownTransaction[]>([])
  const [accounts, setAccounts] = useState<Record<number, AccountOption>>({})
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const [reload, setReload] = useState(0)

  const key = filters ? JSON.stringify(filters) : ""

  useEffect(() => {
    if (!filters) return
    let cancelled = false
    setRows([])
    setLoading(true)
    setFailed(false)
    const params = new URLSearchParams({
      month: String(filters.month),
      year: String(filters.year),
      period: "true",
      type: "Sortie",
      is_transfer: "false",
      limit: "500",
    })
    if (filters.categoryId === null) params.set("uncategorized", "true")
    else if (filters.categoryId !== undefined) params.set("category_id", String(filters.categoryId))
    if (filters.merchantName) params.set("merchant_name", filters.merchantName)
    if (filters.accountId) params.set("account_id", String(filters.accountId))
    else params.set("budget_scope", "true")

    Promise.all([
      api.get<DrilldownTransaction[]>(`/transactions?${params.toString()}`),
      api.get<AccountOption[]>("/accounts"),
    ])
      .then(([txs, accs]) => {
        if (cancelled) return
        setRows(txs)
        setAccounts(Object.fromEntries(accs.map((a) => [a.id, a])))
      })
      .catch(() => !cancelled && setFailed(true))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, reload])

  // Montant attribué à la catégorie filtrée : la part pour une dépense découpée, net des remboursements
  const shareOf = (tx: DrilldownTransaction) => {
    const net = tx.amount - (tx.reimbursement_offset ?? 0)
    if (filters?.categoryId && tx.splits?.length) {
      const part = tx.splits.filter((s) => s.category_id === filters.categoryId).reduce((sum, s) => sum + s.amount, 0)
      return tx.amount ? (net * part) / tx.amount : 0
    }
    return net
  }

  const currencyOf = (tx: DrilldownTransaction) => accounts[tx.account_id]?.currency ?? "EUR"
  const sameCurrency = rows.every((tx) => currencyOf(tx) === "EUR")
  const total = rows.reduce((sum, tx) => sum + shareOf(tx), 0)

  return (
    <Sheet open={filters !== null} onOpenChange={(open) => !open && closeDrilldown()}>
      <SheetContent side="right" className="flex w-full flex-col gap-4 overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 pr-6">
            <ListFilter className="h-5 w-5 text-slate-400" />
            {filters?.label}
          </SheetTitle>
          <SheetDescription>
            Dépenses de {filters ? `${MONTHS[filters.month - 1]} ${filters.year}` : ""}
            {filters?.accountId && accounts[filters.accountId] ? ` · ${accounts[filters.accountId].name}` : ""}
            {!loading && rows.length > 0 && sameCurrency && <> · {rows.length} opérations · {formatCurrency(total)}</>}
          </SheetDescription>
        </SheetHeader>

        {failed ? (
          <ErrorState message="Les transactions n'ont pas pu être chargées." onRetry={() => setReload((n) => n + 1)} />
        ) : loading ? (
          <div className="space-y-2">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-14 rounded-xl" />)}</div>
        ) : rows.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-500">Aucune dépense ne correspond (les versements d'investissement n'apparaissent pas ici).</p>
        ) : (
          <ul className="divide-y rounded-xl border">
            {rows.map((tx) => {
              const share = shareOf(tx)
              const isPart = filters?.categoryId && (tx.splits?.length ?? 0) > 0
              return (
                <li key={tx.id}>
                  <Link
                    to={`/accounts/${tx.account_id}`}
                    className="flex min-h-14 items-center gap-3 px-3 py-2 hover:bg-slate-50"
                    onClick={closeDrilldown}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">{tx.merchant_obj?.name ?? tx.merchant}</p>
                      <p className="truncate text-xs text-slate-500">
                        {format(parseISO(tx.date), "d MMM", { locale: fr })}
                        {accounts[tx.account_id] ? ` · ${accounts[tx.account_id].name}` : ""}
                        {!filters?.categoryId && tx.category ? ` · ${tx.category.name}` : ""}
                        {tx.note ? ` · ${tx.note}` : ""}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-semibold tabular-nums text-slate-900">{formatCurrency(share, currencyOf(tx))}</p>
                      {isPart && (
                        <p className="flex items-center justify-end gap-1 text-[11px] text-slate-400">
                          <Split className="h-3 w-3" />sur {formatCurrency(tx.amount, currencyOf(tx))}
                        </p>
                      )}
                    </div>
                    <ArrowRight className="h-4 w-4 shrink-0 text-slate-300" />
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </SheetContent>
    </Sheet>
  )
}
