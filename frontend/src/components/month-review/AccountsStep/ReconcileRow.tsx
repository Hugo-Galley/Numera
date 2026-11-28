/** Un compte bancaire à rapprocher : solde de Numera à la date du relevé, champ du solde de la banque, écart et causes. */
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

import { ReconcileHints, type ReconcileResult } from "@/components/accounts/ReconcileHints"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useSubmit } from "@/hooks/useSubmit"
import { postAccountsReconcile } from "@/lib/api/accounts"
import { errorMessage, formatCurrency } from "@/lib/utils"
import type { ReviewAccount } from "@/types/monthReview"

/** « 1 248,30 » ou « 1248.30 » → 1248.3 ; `null` si la saisie n'est pas un nombre. */
function parseAmount(raw: string): number | null {
  const cleaned = raw.replace(/\s/g, "").replace(",", ".")
  if (cleaned === "") return null
  const value = Number(cleaned)
  return Number.isFinite(value) ? value : null
}

interface Props {
  account: ReviewAccount
  busy: boolean
  inputRef: (el: HTMLInputElement | null) => void
  /** « Valider sans saisir » */
  onVerify: () => void
  /** Les soldes collent : le compte est validé côté serveur. */
  onReconciled: () => void
}

export function ReconcileRow({ account, busy, inputRef, onVerify, onReconciled }: Props) {
  const { t } = useTranslation("month")
  const [value, setValue] = useState("")
  const [result, setResult] = useState<ReconcileResult | null>(null)

  const [check, checking] = useSubmit(async () => {
    const bankBalance = parseAmount(value)
    if (bankBalance === null) {
      toast.error(t("accountsStep.saisisUnMontant"))
      return
    }
    try {
      const res = await postAccountsReconcile<ReconcileResult>(account.id, { date: account.statement_date, bank_balance: bankBalance })
      setResult(res)
      if (res.verified) {
        toast.success(t("accountsStep.soldeValide"))
        onReconciled()
      }
    } catch (e) {
      toast.error(errorMessage(e, t("accountsStep.echecDuRapprochement")))
    }
  })

  const verified = account.verified_since_month_end
  const gap = result && !result.matches ? result.gap : null

  return (
    <li className="space-y-3 rounded-xl border border-slate-200 p-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="truncate font-medium">{account.name}</p>
          <p className="text-xs text-slate-500">
            {t("accountsStep.numera")}{" "}
            <span className="amount-blur font-semibold tabular-nums text-slate-700">
              {formatCurrency(account.statement_balance ?? 0, account.currency)}
            </span>
          </p>
        </div>
        {verified ? (
          <span className="flex items-center gap-1 text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4" /> {t("accountsStep.valide")}
          </span>
        ) : (
          <form className="flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); check() }}>
            <Input
              ref={inputRef}
              inputMode="decimal"
              autoComplete="off"
              aria-label={t("accountsStep.soldeDuReleveDe", { name: account.name })}
              placeholder={t("accountsStep.soldeDuReleve")}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="h-10 w-full text-base sm:w-40 md:h-9 md:text-sm"
            />
            <Button type="submit" size="sm" variant="outline" className="h-10 shrink-0 md:h-9" disabled={checking || value.trim() === ""}>
              {checking ? t("accountsStep.verification") : t("accountsStep.verifier")}
            </Button>
          </form>
        )}
      </div>

      {!verified && gap !== null && result && (
        <div className="space-y-2">
          <p className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm font-medium text-amber-900">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span className="amount-blur">
              {t("accountsStep.ecartDe", { gap: `${gap > 0 ? "+" : ""}${formatCurrency(gap, result.currency)}` })}
            </span>
          </p>
          <ReconcileHints hints={result.hints} currency={result.currency} />
          <Link to={`/accounts/${account.id}`} className="inline-flex min-h-10 items-center text-sm font-medium text-slate-700 underline underline-offset-4">
            {t("accountsStep.ouvrirLeCompte")}
          </Link>
        </div>
      )}

      {!verified && (
        <button
          type="button"
          className="min-h-10 text-xs text-slate-500 underline underline-offset-4 hover:text-slate-700 disabled:opacity-50 md:min-h-0"
          disabled={busy}
          onClick={onVerify}
        >
          {t("accountsStep.validerSansSaisir")}
        </button>
      )}
    </li>
  )
}
