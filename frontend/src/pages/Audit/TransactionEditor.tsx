import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { RefreshCw, Save, Trash2 } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import { toNaiveLocal } from "@/lib/dates"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useState } from "react"
import { Account, Category, Transaction, toDateTimeLocal } from "./types"

export function TransactionEditor({
  tx,
  categories,
  accounts,
  onSaved,
  onDeleted,
}: {
  tx: Transaction
  categories: Category[]
  accounts: Account[]
  onSaved: (tx: Transaction) => void
  onDeleted?: (id: number) => void
}) {
  const confirm = useConfirm()
  const [draft, setDraft] = useState({
    date: toDateTimeLocal(tx.date),
    type: tx.type,
    merchant: tx.merchant || "",
    category_id: tx.category_id ? String(tx.category_id) : "none",
    amount: String(tx.amount),
    note: tx.note || "",
  })
  const [saving, setSaving] = useState(false)

  const account = accounts.find((a) => a.id === tx.account_id)

  async function save() {
    setSaving(true)
    try {
      const saved = await api.patch<Transaction>(`/transactions/${tx.id}`, {
        date: draft.date ? toNaiveLocal(draft.date) : undefined,
        type: draft.type,
        merchant: draft.merchant.trim(),
        category_id: draft.category_id === "none" ? null : Number(draft.category_id),
        amount: Number(draft.amount),
        note: draft.note.trim() || null,
      })
      onSaved(saved)
      toast.success("Transaction enregistrée")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sauvegarde impossible")
    } finally {
      setSaving(false)
    }
  }

  async function remove() {
    if (!(await confirm(`Supprimer la transaction « ${tx.merchant} » de ${formatCurrency(tx.amount)} ?`))) return
    setSaving(true)
    try {
      await api.delete(`/transactions/${tx.id}`)
      onDeleted?.(tx.id)
      toast.success("Transaction supprimée")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Suppression impossible")
    } finally {
      setSaving(false)
    }
  }

  // Une sortie ne se catégorise pas en Salaire ou Dividendes ; la catégorie actuelle reste toujours visible
  const categoryOptions = categories.filter(
    (c) => draft.type !== "Sortie" || c.type !== "revenu" || String(c.id) === draft.category_id
  )

  return (
    <div className="rounded-md border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="flex flex-col p-3 gap-3 lg:hidden">
        <div className="flex items-center justify-between border-b pb-2">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Compte</p>
            <p className="truncate text-xs font-bold text-slate-700">{account?.name || `ID: ${tx.account_id}`}</p>
          </div>
          <Badge variant="outline" className="text-[10px]">{tx.currency}</Badge>
        </div>
        
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">Date et heure</p>
            <Input
              type="datetime-local"
              value={draft.date}
              onChange={(event) => setDraft({ ...draft, date: event.target.value })}
              className="h-11 text-base"
            />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">Type</p>
            <Select value={draft.type} onValueChange={(value) => setDraft({ ...draft, type: value })}>
              <SelectTrigger className="h-11 text-base">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Sortie">Sortie</SelectItem>
                <SelectItem value="Entree">Entrée</SelectItem>
                <SelectItem value="Interets">Intérêts</SelectItem>
                <SelectItem value="Solde Initial">Solde Initial</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Marchand</p>
          <Input
            value={draft.merchant}
            onChange={(event) => setDraft({ ...draft, merchant: event.target.value })}
            placeholder="Marchand"
            className="h-11 text-base"
          />
        </div>

        <div className="grid grid-cols-[1.5fr_1fr] gap-3">
          <div className="min-w-0">
            <p className="mb-1 text-xs font-medium text-slate-500">Catégorie</p>
            <Select value={draft.category_id} onValueChange={(value) => setDraft({ ...draft, category_id: value })}>
              <SelectTrigger className="h-11 text-base">
                <SelectValue placeholder="Catégorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sans catégorie</SelectItem>
                {categoryOptions.map((category) => (
                  <SelectItem key={category.id} value={String(category.id)}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">Montant</p>
            <Input
              type="number" inputMode="decimal"
              min="0"
              step="0.01"
              value={draft.amount}
              onChange={(event) => setDraft({ ...draft, amount: event.target.value })}
              className="h-11 text-base font-bold"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t pt-3">
          {onDeleted && (
            <Button aria-label="Supprimer" type="button" variant="outline" size="icon" onClick={remove} disabled={saving} className="h-11 w-11 text-rose-500 hover:bg-rose-50 hover:text-rose-600">
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          <Button type="button" size="sm" onClick={save} disabled={saving || !draft.merchant.trim() || Number(draft.amount) <= 0} className="h-11 shadow-sm flex-1">
            {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Enregistrer
          </Button>
        </div>
      </div>

      <div className="hidden lg:block overflow-x-auto">
        <div className="flex items-center gap-4 p-3 min-w-[1000px]">
          <div className="w-[140px] shrink-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Compte</p>
            <p className="truncate text-xs font-bold text-slate-700">{account?.name || `ID: ${tx.account_id}`}</p>
          </div>

          <div className="w-[160px] shrink-0">
            <Input
              type="datetime-local"
              value={draft.date}
              onChange={(event) => setDraft({ ...draft, date: event.target.value })}
              className="h-9 text-xs"
            />
          </div>
          
          <div className="w-[110px] shrink-0">
            <Select value={draft.type} onValueChange={(value) => setDraft({ ...draft, type: value })}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Sortie">Sortie</SelectItem>
                <SelectItem value="Entree">Entrée</SelectItem>
                <SelectItem value="Interets">Intérêts</SelectItem>
                <SelectItem value="Solde Initial">Solde Initial</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <Input
              value={draft.merchant}
              onChange={(event) => setDraft({ ...draft, merchant: event.target.value })}
              placeholder="Marchand"
              className="h-9 text-xs"
            />
          </div>

          <div className="w-[160px] shrink-0">
            <Select value={draft.category_id} onValueChange={(value) => setDraft({ ...draft, category_id: value })}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Catégorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sans catégorie</SelectItem>
                {categoryOptions.map((category) => (
                  <SelectItem key={category.id} value={String(category.id)}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="w-[100px] shrink-0">
            <div className="relative">
              <Input
                type="number" inputMode="decimal"
                min="0"
                step="0.01"
                value={draft.amount}
                onChange={(event) => setDraft({ ...draft, amount: event.target.value })}
                className="h-9 pr-8 text-xs font-bold"
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-400">
                {tx.currency}
              </span>
            </div>
          </div>

          <div className="w-[140px] shrink-0">
            <Input
              value={draft.note}
              onChange={(event) => setDraft({ ...draft, note: event.target.value })}
              placeholder="Note"
              className="h-9 text-xs"
            />
          </div>

          <div className="flex shrink-0 gap-2">
            {onDeleted && (
              <Button aria-label="Supprimer" type="button" variant="outline" size="icon" onClick={remove} disabled={saving} className="h-9 w-9 text-rose-500 hover:bg-rose-50 hover:text-rose-600">
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
            <Button type="button" size="sm" onClick={save} disabled={saving || !draft.merchant.trim() || Number(draft.amount) <= 0} className="h-9 shadow-sm">
              {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Enregistrer
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
