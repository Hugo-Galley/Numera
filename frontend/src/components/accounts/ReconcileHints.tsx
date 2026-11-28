import { AlertTriangle, Copy, Repeat, Search } from "lucide-react"
import { format, parseISO } from "date-fns"

import { formatCurrency } from "@/lib/utils"

interface ReconcileTransaction {
  id: number
  date: string
  merchant: string
  type: string
  amount: number
}

export interface ReconcileHint {
  kind: "duplicate" | "extra_or_missing" | "wrong_sign" | "missing"
  message: string
  transactions: ReconcileTransaction[]
}

/** Réponse de `POST /accounts/{id}/reconcile`. */
export interface ReconcileResult {
  currency: string
  bank_balance: number
  numera_balance: number
  gap: number
  matches: boolean
  verified: boolean
  hints: ReconcileHint[]
}

const HINT_ICONS = {
  duplicate: Copy,
  extra_or_missing: Search,
  wrong_sign: Repeat,
  missing: AlertTriangle,
}

/** Causes probables d'un écart de rapprochement, avec les transactions concernées. */
export function ReconcileHints({ hints, currency }: { hints: ReconcileHint[]; currency: string }) {
  return (
    <>
      {hints.map((hint, i) => {
        const Icon = HINT_ICONS[hint.kind] ?? Search
        return (
          <div key={i} className="rounded-xl border border-slate-200 p-3 text-sm">
            <p className="flex gap-2 text-slate-700">
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
              <span>{hint.message}</span>
            </p>
            {hint.transactions.length > 0 && (
              <ul className="mt-2 space-y-1 pl-6">
                {hint.transactions.map((tx) => (
                  <li key={tx.id} className="flex justify-between gap-3 text-xs text-slate-500">
                    <span className="truncate">{format(parseISO(tx.date), "dd/MM/yyyy")} · {tx.merchant}</span>
                    <span className={`shrink-0 tabular-nums ${tx.type === "Sortie" ? "text-rose-600" : "text-emerald-600"}`}>
                      {tx.type === "Sortie" ? "- " : "+ "}{formatCurrency(tx.amount, currency)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )
      })}
    </>
  )
}
