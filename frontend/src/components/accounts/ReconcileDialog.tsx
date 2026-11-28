import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CheckCircle2 } from "lucide-react"
import { format, parseISO } from "date-fns"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { todayLocal } from "@/lib/dates"
import { errorMessage, formatCurrency } from "@/lib/utils"
import { useSubmit } from "@/hooks/useSubmit"
import { postAccountsReconcile } from "@/lib/api/accounts"
import { ReconcileHints, type ReconcileResult } from "@/components/accounts/ReconcileHints"

interface Props {
  account: { id: number; name: string; currency: string } | null
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Appelé quand le compte a été marqué vérifié (écart nul) */
  onVerified?: () => void
}

/** Compare le solde affiché par la banque à celui de Numera et liste les causes probables d'un écart. */
export function ReconcileDialog({ account, open, onOpenChange, onVerified }: Props) {
  const { t } = useTranslation("accounts")
  const [day, setDay] = useState(todayLocal())
  const [balance, setBalance] = useState("")
  const [result, setResult] = useState<ReconcileResult | null>(null)

  useEffect(() => {
    if (open) {
      setDay(todayLocal())
      setBalance("")
      setResult(null)
    }
  }, [open, account?.id])

  const [handleCheck, busy] = useSubmit(async () => {
    if (!account) return
    const value = parseFloat(balance.replace(/\s/g, "").replace(",", "."))
    if (!Number.isFinite(value) || !day) {
      toast.error(t("reconcile.needInput"))
      return
    }
    try {
      const res = await postAccountsReconcile<ReconcileResult>(account.id, { date: day, bank_balance: value })
      setResult(res)
      if (res.verified) {
        toast.success(t("reconcile.verified"))
        onVerified?.()
      }
    } catch (e) {
      toast.error(errorMessage(e, t("reconcile.error")))
    }
  })

  const currency = account?.currency ?? "EUR"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[480px] rounded-2xl max-h-[calc(100dvh-2rem)] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t("reconcile.title")}</DialogTitle>
          <DialogDescription>
            {t("reconcile.hint", { name: account?.name ?? t("reconcile.thisAccount") })}
          </DialogDescription>
        </DialogHeader>

        <form
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
          onSubmit={(e) => { e.preventDefault(); handleCheck() }}
        >
          <div className="grid gap-2">
            <Label htmlFor="reconcile-date">{t("reconcile.date")}</Label>
            <Input id="reconcile-date" type="date" value={day} max={todayLocal()} onChange={(e) => setDay(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="reconcile-balance">{t("reconcile.bankBalance", { currency })}</Label>
            <Input
              id="reconcile-balance"
              inputMode="decimal"
              autoFocus
              placeholder="0,00"
              value={balance}
              onChange={(e) => setBalance(e.target.value)}
            />
          </div>
          <button type="submit" hidden />
        </form>

        {result && (
          <div className="space-y-3">
            <div className={`rounded-xl border p-3 text-sm ${result.matches ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
              {result.matches ? (
                <p className="flex items-center gap-2 font-medium">
                  <CheckCircle2 className="h-4 w-4" /> {t("reconcile.match", { date: format(parseISO(day), "dd/MM/yyyy") })}
                </p>
              ) : (
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <p className="text-xs opacity-75">{t("reconcile.bank")}</p>
                    <p className="font-semibold tabular-nums">{formatCurrency(result.bank_balance, currency)}</p>
                  </div>
                  <div>
                    <p className="text-xs opacity-75">Numera</p>
                    <p className="font-semibold tabular-nums">{formatCurrency(result.numera_balance, currency)}</p>
                  </div>
                  <div>
                    <p className="text-xs opacity-75">{t("reconcile.gap")}</p>
                    <p className="font-bold tabular-nums">{result.gap > 0 ? "+" : ""}{formatCurrency(result.gap, currency)}</p>
                  </div>
                </div>
              )}
            </div>

            <ReconcileHints hints={result.hints} currency={currency} />
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>{t("reconcile.close")}</Button>
          <Button onClick={() => handleCheck()} disabled={busy || !balance} className="bg-slate-900 text-white">
            {busy ? t("reconcile.verifying") : t("reconcile.verify")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
