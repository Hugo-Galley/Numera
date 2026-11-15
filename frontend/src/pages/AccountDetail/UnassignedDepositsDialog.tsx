import { useEffect, useState } from "react"
import { format } from "date-fns"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { SecuritySearchInput, type SelectedAsset } from "@/components/investments/SecuritySearchInput"
import { dateLocale } from "@/i18n/locale"
import { getInvestmentTransactions, getInvestmentTransactionsSecurityProposal, patchInvestmentTransactionsById } from "@/lib/api/investments"
import { getRecurringTransactions, patchRecurringTransactionsById } from "@/lib/api/recurring"
import type { ApiResponse } from "@/lib/api/types"
import { errorMessage, formatCurrency } from "@/lib/utils"

type Deposit = ApiResponse<"/investment-transactions", "get">[number]

interface Draft {
  ticker: string
  isin: string
  etfProfileId: number | null
  quantity: string
  unitPrice: string
  priceCurrency: string | null
  /** Date du cours proposé ; `null` = aucun cours connu ; `undefined` = pas encore demandé. */
  priceDate: string | null | undefined
  applyToRule: boolean
}

const EMPTY: Draft = { ticker: "", isin: "", etfProfileId: null, quantity: "", unitPrice: "", priceCurrency: null, priceDate: undefined, applyToRule: false }

const day = (iso: string) => format(new Date(iso), "P", { locale: dateLocale() })

/** Pop-in ouverte à l'arrivée sur un compte titres : versements créés par une récurrence et rattachés à
 * aucun titre, présentés un par un pour être reliés (titre, quantité, prix) ou laissés en espèces.
 * La liste et la taille proposée viennent du backend ; `onDone` recharge la page après chaque écriture. */
export function UnassignedDepositsDialog({ accountId, onDone }: { accountId: number; onDone: () => void }) {
  const { t } = useTranslation("accountDetail")
  const [deposits, setDeposits] = useState<Deposit[]>([])
  const [total, setTotal] = useState(0)
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<Draft>(EMPTY)
  const [busy, setBusy] = useState(false)
  const [ruleNames, setRuleNames] = useState<Record<number, string>>({})

  useEffect(() => {
    let cancelled = false
    getInvestmentTransactions(`?account_id=${accountId}&unassigned=true`)
      .then(rows => {
        if (cancelled || rows.length === 0) return
        setDeposits(rows)
        setTotal(rows.length)
        setOpen(true)
        // Nom des récurrences à l'origine des versements (libellé de la case à cocher)
        getRecurringTransactions()
          .then(rules => { if (!cancelled) setRuleNames(Object.fromEntries(rules.map(r => [r.id, r.name]))) })
          .catch(() => undefined)
      })
      .catch(() => undefined) // la pop-in est une aide : une panne ne bloque pas la page
    return () => { cancelled = true }
  }, [accountId])

  const deposit = deposits[0]
  if (!deposit) return null
  const ruleId = deposit.recurring_transaction_id ?? null
  const ruleName = ruleId !== null ? ruleNames[ruleId] : undefined

  const next = () => {
    setDraft(EMPTY)
    setDeposits(rest => rest.slice(1))
    if (deposits.length <= 1) setOpen(false)
    onDone()
  }

  const selectAsset = async (asset: SelectedAsset) => {
    setDraft(d => ({ ...d, ticker: asset.symbol, isin: asset.isin ?? "", etfProfileId: asset.etf_profile_id ?? null, priceDate: undefined }))
    try {
      const proposal = await getInvestmentTransactionsSecurityProposal(deposit.id, `?ticker=${encodeURIComponent(asset.symbol)}`)
      setDraft(d => d.ticker !== asset.symbol ? d : {
        ...d,
        quantity: proposal.quantity != null ? String(proposal.quantity) : d.quantity,
        unitPrice: proposal.unit_price != null ? String(proposal.unit_price) : d.unitPrice,
        priceCurrency: proposal.price_currency ?? null,
        priceDate: proposal.price_date ?? null,
      })
    } catch {
      setDraft(d => ({ ...d, priceDate: null }))
    }
  }

  const link = async () => {
    const ticker = draft.ticker.trim()
    const quantity = Number(draft.quantity)
    if (!ticker || !(quantity > 0)) {
      toast.error(t("unassignedDeposits.titreEtQuantiteRequis"))
      return
    }
    setBusy(true)
    try {
      await patchInvestmentTransactionsById(deposit.id, {
        ticker,
        isin: draft.isin || null,
        quantity,
        unit_price: Number(draft.unitPrice) > 0 ? Number(draft.unitPrice) : null,
        price_currency: draft.priceCurrency,
        etf_profile_id: draft.etfProfileId,
      })
      if (draft.applyToRule && ruleId !== null) {
        await patchRecurringTransactionsById(ruleId, { ticker, isin: draft.isin || null, etf_profile_id: draft.etfProfileId })
      }
      toast.success(t("unassignedDeposits.versementRelie", { ticker }))
      next()
    } catch (err) {
      toast.error(errorMessage(err, t("unassignedDeposits.echec")))
    } finally {
      setBusy(false)
    }
  }

  const keepAsCash = async () => {
    setBusy(true)
    try {
      await patchInvestmentTransactionsById(deposit.id, { kept_as_cash: true })
      toast.success(t("unassignedDeposits.laisseEnEspeces"))
      next()
    } catch {
      toast.error(t("unassignedDeposits.echec"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[460px] max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-baseline justify-between gap-3 text-2xl font-bold">
            {t("unassignedDeposits.titre")}
            {total > 1 && (
              <span className="text-xs font-medium text-slate-400">
                {t("unassignedDeposits.position", { current: total - deposits.length + 1, total })}
              </span>
            )}
          </DialogTitle>
          <DialogDescription>{t("unassignedDeposits.description")}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 py-2">
          <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-slate-900">{deposit.note || ruleName}</p>
              <p className="text-xs text-slate-500">{day(deposit.date)}</p>
            </div>
            <span className="amount-blur shrink-0 text-lg font-black text-emerald-600">{formatCurrency(deposit.amount, deposit.currency)}</span>
          </div>

          <SecuritySearchInput
            ticker={draft.ticker}
            isin={draft.isin}
            onSelectAsset={selectAsset}
            onChangeTicker={ticker => setDraft(d => ({ ...d, ticker }))}
            onChangeIsin={isin => setDraft(d => ({ ...d, isin }))}
          />

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="unassigned-quantity" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("unassignedDeposits.quantite")}</Label>
              <Input id="unassigned-quantity" type="number" inputMode="decimal" step="any" value={draft.quantity}
                onChange={e => setDraft(d => ({ ...d, quantity: e.target.value }))} className="bg-slate-50 border-slate-200" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="unassigned-price" className="text-xs uppercase tracking-wider font-bold text-slate-500">
                {t("unassignedDeposits.prixUnitaire")}{draft.priceCurrency ? ` (${draft.priceCurrency})` : ""}
              </Label>
              <Input id="unassigned-price" type="number" inputMode="decimal" step="any" value={draft.unitPrice}
                onChange={e => setDraft(d => ({ ...d, unitPrice: e.target.value }))} className="bg-slate-50 border-slate-200" />
            </div>
          </div>
          {draft.priceDate !== undefined && (
            <p className="-mt-3 text-xs text-slate-500">
              {draft.priceDate ? t("unassignedDeposits.coursDu", { date: day(draft.priceDate) }) : t("unassignedDeposits.coursInconnu")}
            </p>
          )}

          {ruleName && (
            <label className="flex items-start gap-2 text-sm text-slate-700">
              <Checkbox checked={draft.applyToRule} onCheckedChange={v => setDraft(d => ({ ...d, applyToRule: v === true }))} className="mt-0.5" />
              <span>{t("unassignedDeposits.appliquerALaRecurrence", { name: ruleName })}</span>
            </label>
          )}
        </div>

        <DialogFooter className="gap-2 sm:justify-between">
          <Button variant="ghost" onClick={() => setOpen(false)} disabled={busy}>{t("unassignedDeposits.plusTard")}</Button>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button variant="outline" onClick={keepAsCash} disabled={busy}>{t("unassignedDeposits.laisserEnEspeces")}</Button>
            <Button onClick={link} disabled={busy}>{t("unassignedDeposits.relier")}</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
