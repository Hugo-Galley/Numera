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
        toast.error("Impossible d'estimer les PRU")
        onOpenChange(false)
      })
  }, [open, accountId, onOpenChange])

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
      toast.success(`${selected.length} PRU enregistré${selected.length > 1 ? "s" : ""}`)
      onApplied()
      onOpenChange(false)
    } catch (err: any) {
      toast.error(err?.message || "Erreur lors de l'enregistrement")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Estimer les PRU</DialogTitle>
          <DialogDescription>
            Calculé depuis les achats saisis avant ton Point Zéro (prix × quantité + frais, moyenne pondérée). Compare avec ton courtier et corrige si besoin : rien n'est enregistré avant que tu valides.
          </DialogDescription>
        </DialogHeader>

        {rows === null ? (
          <Skeleton className="h-40 w-full" />
        ) : rows.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">Aucune ligne dans l'inventaire du Point Zéro.</p>
        ) : (
          <div className="space-y-2">
            {rows.map((r) => {
              const line = lines[r.ticker]
              const partial = r.coverage !== null && r.coverage < 0.99
              return (
                <div key={r.ticker} className="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 shrink-0"
                    checked={line?.checked ?? false}
                    onChange={(e) => update(r.ticker, { checked: e.target.checked })}
                    aria-label={`Appliquer le PRU de ${r.ticker}`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-900">{r.asset_name}</p>
                    <p className="font-mono text-[11px] text-slate-400">
                      {r.ticker} • {r.quantity} parts
                      {r.current_cost !== null && ` • PRU actuel ${r.current_cost} ${r.currency}`}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {r.estimate === null ? (
                        <Badge variant="outline" className="font-normal text-slate-500">Aucun achat saisi : à renseigner à la main</Badge>
                      ) : (
                        <Badge variant="secondary" className="font-normal">{r.buys} achat{r.buys > 1 ? "s" : ""}</Badge>
                      )}
                      {r.method === "amounts" && (
                        <Badge
                          variant="outline"
                          className="border-amber-300 font-normal text-amber-700"
                          title="Tes anciens versements n'ont pas de quantité : PRU = total versé ÷ parts détenues. Exact si tous tes achats de ce titre sont saisis."
                        >
                          Estimé : total versé ÷ parts
                        </Badge>
                      )}
                      {partial && (
                        <Badge variant="outline" className="border-amber-300 font-normal text-amber-700" title="Des parts détenues avant le premier achat saisi ne sont pas prises en compte">
                          Couvre {Math.round((r.coverage ?? 0) * 100)} % des parts
                        </Badge>
                      )}
                      {r.sold_quantity > 0 && <Badge variant="outline" className="font-normal">{r.sold_quantity} vendue(s)</Badge>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      step="0.0001"
                      min="0"
                      className="h-8 w-32 text-right font-mono"
                      value={line?.value ?? ""}
                      onChange={(e) => update(r.ticker, { value: e.target.value, checked: Number(e.target.value) > 0 })}
                      placeholder="PRU"
                    />
                    <span className="w-9 text-xs text-slate-500">{r.currency}</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={apply} disabled={saving || selected.length === 0}>
            {saving ? "Enregistrement..." : `Enregistrer ${selected.length} PRU`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
