import { useEffect, useMemo, useState } from "react"
import { Plus, Split, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api } from "@/lib/api"
import { useSubmit } from "@/hooks/useSubmit"
import { errorMessage, formatCurrency } from "@/lib/utils"

export interface SplitPart {
  id?: number
  category_id: number | null
  amount: number
  note?: string | null
}

export interface SplittableTransaction {
  id: number
  merchant: string
  amount: number
  currency: string
  category_id: number | null
  splits?: SplitPart[]
}

interface CategoryOption {
  id: number
  name: string
  type?: string
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: SplittableTransaction | null
  categories: CategoryOption[]
  onDone: () => void
}

interface Row {
  categoryId: string
  amount: string
}

// Mêmes exclusions que le backend (core/splits.py) : une part ne change pas la nature de la dépense
const isSplittableCategory = (c: CategoryOption) =>
  c.type !== "revenu" && c.name !== "Investissement" && c.name !== "Epargne"

const parseAmount = (value: string) => parseFloat(value.replace(",", "."))
const toCents = (value: number) => Math.round(value * 100)

export function SplitTransactionDialog({ open, onOpenChange, transaction, categories, onDone }: Props) {
  const [rows, setRows] = useState<Row[]>([])

  useEffect(() => {
    if (!open || !transaction) return
    if (transaction.splits && transaction.splits.length > 0) {
      setRows(transaction.splits.map((s) => ({ categoryId: s.category_id ? String(s.category_id) : "", amount: String(s.amount) })))
    } else {
      setRows([
        { categoryId: transaction.category_id ? String(transaction.category_id) : "", amount: String(transaction.amount) },
        { categoryId: "", amount: "" },
      ])
    }
  }, [open, transaction])

  const options = useMemo(() => categories.filter(isSplittableCategory), [categories])
  const total = transaction?.amount ?? 0
  const allocatedCents = rows.reduce((sum, r) => sum + (Number.isFinite(parseAmount(r.amount)) ? toCents(parseAmount(r.amount)) : 0), 0)
  const remainingCents = toCents(total) - allocatedCents
  const isValid =
    rows.length >= 2 &&
    remainingCents === 0 &&
    rows.every((r) => r.categoryId && parseAmount(r.amount) > 0)

  const update = (index: number, patch: Partial<Row>) =>
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)))

  // Double-clic sur un montant : y reporter ce qu'il reste à répartir
  const fillRemaining = (index: number) => {
    const current = parseAmount(rows[index].amount) || 0
    update(index, { amount: ((toCents(current) + remainingCents) / 100).toFixed(2) })
  }

  const [save, saving] = useSubmit(async () => {
    if (!transaction) return
    try {
      await api.put(`/transactions/${transaction.id}/splits`, {
        items: rows.map((r) => ({ category_id: Number(r.categoryId), amount: parseAmount(r.amount) })),
      })
      toast.success("Dépense découpée")
      onOpenChange(false)
      onDone()
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors du découpage"))
    }
  })

  const [cancelSplit, cancelling] = useSubmit(async () => {
    if (!transaction) return
    try {
      await api.put(`/transactions/${transaction.id}/splits`, { items: [] })
      toast.success("Découpage annulé")
      onOpenChange(false)
      onDone()
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de l'annulation"))
    }
  })

  const hasSplits = (transaction?.splits?.length ?? 0) > 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Split className="h-5 w-5 text-slate-500" />
            Découper la dépense
          </DialogTitle>
          <DialogDescription>
            {transaction?.merchant} · {formatCurrency(total, transaction?.currency)}. Chaque part compte dans sa catégorie
            (budget, répartition, alertes) ; le total de la dépense ne change pas.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          {rows.map((row, index) => (
            <div key={index} className="flex items-center gap-2">
              <Select value={row.categoryId} onValueChange={(v) => update(index, { categoryId: v })}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Catégorie" />
                </SelectTrigger>
                <SelectContent>
                  {options.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                inputMode="decimal"
                className="w-28 text-right"
                value={row.amount}
                placeholder="0,00"
                onChange={(e) => update(index, { amount: e.target.value })}
                onDoubleClick={() => fillRemaining(index)}
              />
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 shrink-0"
                disabled={rows.length <= 2}
                onClick={() => setRows((prev) => prev.filter((_, i) => i !== index))}
                title="Retirer la part"
              >
                <Trash2 className="h-4 w-4 text-slate-400" />
              </Button>
            </div>
          ))}
          <div className="flex items-center justify-between pt-1">
            <Button variant="outline" size="sm" onClick={() => setRows((prev) => [...prev, { categoryId: "", amount: "" }])}>
              <Plus className="mr-1 h-4 w-4" />
              Ajouter une part
            </Button>
            <span className={`text-sm tabular-nums ${remainingCents === 0 ? "text-emerald-600" : "text-amber-600"}`}>
              {remainingCents === 0
                ? "Montant réparti"
                : `Reste ${formatCurrency(remainingCents / 100, transaction?.currency)}`}
            </span>
          </div>
          <p className="text-xs text-slate-400">Double-cliquez sur un montant pour y reporter le reste.</p>
        </div>

        <DialogFooter className="gap-2 sm:justify-between">
          {hasSplits ? (
            <Button variant="ghost" className="text-rose-600" onClick={cancelSplit} disabled={cancelling}>
              Annuler le découpage
            </Button>
          ) : <span />}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Fermer</Button>
            <Button onClick={save} disabled={!isValid || saving} className="bg-slate-900 text-white">
              Enregistrer
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
