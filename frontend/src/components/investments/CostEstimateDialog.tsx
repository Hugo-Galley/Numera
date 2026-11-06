import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { api } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"

interface CostEstimate {
  ticker: string
  asset_name: string
  quantity: number
  currency: string
  current_cost: number | null
  estimate: number | null
  buys: number
  bought_quantity: number
  sold_quantity: number
  coverage: number | null
  first_buy: string | null
  method: "quantities" | "amounts"
  amount_only_buys: number
}

interface Line {
  checked: boolean
  value: string
}

interface CostEstimateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  accountId: number
  onApplied: () => void
}

export function CostEstimateDialog({ open, onOpenChange, accountId, onApplied }: CostEstimateDialogProps) {
  const { t } = useTranslation("investments")
  const [rows, setRows] = useState<CostEstimate[] | null>(null)
  const [lines, setLines] = useState<Record<string, Line>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setRows(null)
    api
      .get<CostEstimate[]>(`/holdings/estimate-costs?account_id=${accountId}`)
      .then((data) => {
        setRows(data)
        // Coché d'office : estimation complète (inventaire entièrement expliqué par les achats) et PRU encore vide
        setLines(
          Object.fromEntries(
            data.map((r) => [
              r.ticker,
              {
                checked: r.estimate !== null && r.current_cost === null && (r.method === "amounts" || (r.coverage ?? 0) >= 0.99),
                value: r.estimate !== null ? String(r.estimate) : "",
              },
            ])
          )
        )
      })
      .catch(() => {
        toast.error(t("costEstimateDialog.impossibleDEstimerLesPru"))
        onOpenChange(false)
      })
  }, [open, accountId, onOpenChange, t])

  const update = (ticker: string, patch: Partial<Line>) =>
    setLines((prev) => ({ ...prev, [ticker]: { ...prev[ticker], ...patch } }))

  const selected = (rows ?? []).filter((r) => lines[r.ticker]?.checked && Number(lines[r.ticker].value) > 0)

  const apply = async () => {
    setSaving(true)
    try {
      await api.post(`/holdings/apply-costs`, {
        account_id: accountId,
        items: selected.map((r) => ({ ticker: r.ticker, buy_price_avg: Number(lines[r.ticker].value) })),
      })
      toast.success(i18n.t("misc.prusSaved", { ns: "investments", count: selected.length }))
      onApplied()
      onOpenChange(false)
    } catch (err: any) {
      toast.error(err?.message || t("costEstimateDialog.erreurLorsDeLEnregistrement"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{t("costEstimateDialog.estimerLesPru")}</DialogTitle>
          <DialogDescription>
            {t("costEstimateDialog.calculeDepuisLesAchatsSaisis")}
          </DialogDescription>
        </DialogHeader>

        {rows === null ? (
          <Skeleton className="h-40 w-full" />
        ) : rows.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">{t("costEstimateDialog.aucuneLigneDansLInventaire")}</p>
        ) : (
          <div className="space-y-2">
            {rows.map((r) => {
              const line = lines[r.ticker]
              const partial = r.coverage !== null && r.coverage < 0.99
              return (
                <div key={r.ticker} className="flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-center sm:gap-2">
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                  <label className="-m-2 flex h-10 w-10 shrink-0 items-center justify-center sm:m-0 sm:h-auto sm:w-auto sm:pt-0">
                  <input
                    type="checkbox"
                    className="h-5 w-5 shrink-0 sm:h-4 sm:w-4"
                    checked={line?.checked ?? false}
                    onChange={(e) => update(r.ticker, { checked: e.target.checked })}
                    aria-label={i18n.t("misc.applyAvgCost", { ns: "investments", ticker: r.ticker })}
                  />
                  </label>
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm font-semibold text-slate-900 sm:truncate">{r.asset_name}</p>
                    <p className="font-mono text-[11px] text-slate-400">
                      {r.ticker} • {r.quantity} parts
                      {r.current_cost !== null && ` • PRU actuel ${r.current_cost} ${r.currency}`}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {r.estimate === null ? (
                        <Badge variant="outline" className="font-normal text-slate-500">{t("costEstimateDialog.aucunAchatSaisiARenseigner")}</Badge>
                      ) : (
                        <Badge variant="secondary" className="font-normal">{i18n.t("misc.buys", { ns: "investments", count: r.buys })}</Badge>
                      )}
                      {r.method === "amounts" && (
                        <Badge
                          variant="outline"
                          className="border-amber-300 font-normal text-amber-700"
                          title={t("costEstimateDialog.tesAnciensVersementsNOnt")}
                        >
                          {t("costEstimateDialog.estimeTotalVerseParts")}
                        </Badge>
                      )}
                      {partial && (
                        <Badge variant="outline" className="border-amber-300 font-normal text-amber-700" title={t("costEstimateDialog.desPartsDetenuesAvantLe")}>
                          Couvre {Math.round((r.coverage ?? 0) * 100)} % des parts
                        </Badge>
                      )}
                      {r.sold_quantity > 0 && <Badge variant="outline" className="font-normal">{r.sold_quantity} vendue(s)</Badge>}
                    </div>
                  </div>
                  </div>
                  <div className="flex items-center gap-2 pl-10 sm:pl-0">
                    <Input
                      type="number"
                      inputMode="decimal"
                      step="0.0001"
                      min="0"
                      className="h-11 w-full text-right font-mono text-base sm:h-8 sm:w-32 sm:text-sm"
                      value={line?.value ?? ""}
                      onChange={(e) => update(r.ticker, { value: e.target.value, checked: Number(e.target.value) > 0 })}
                      placeholder={t("costEstimateDialog.pru")}
                    />
                    <span className="w-9 shrink-0 text-xs text-slate-500">{r.currency}</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" className="h-11 sm:h-10" onClick={() => onOpenChange(false)}>{t("costEstimateDialog.annuler")}</Button>
          <Button className="h-11 sm:h-10" onClick={apply} disabled={saving || selected.length === 0}>
            {saving ? t("costEstimateDialog.enregistrement") : `Enregistrer ${selected.length} PRU`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
