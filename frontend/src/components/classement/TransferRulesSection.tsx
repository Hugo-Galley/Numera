import { useCallback, useEffect, useState } from "react"
import { ArrowRight, ArrowRightLeft, History, Pencil, Plus, Trash2 } from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { AccountLite, TransferApplyResult, TransferRule } from "@/types/transfers"
import { useConfirm } from "@/providers/ConfirmProvider"

const EMPTY_FORM = { source: "", dest: "", pattern: "", amount: "", tolerance: "1", days: "5" }

// Règles de virement interne (les suggestions et virements liés sont dans le Centre d'actions)
export function TransferRulesSection() {
  const confirm = useConfirm()
  const [rules, setRules] = useState<TransferRule[]>([])
  const [accounts, setAccounts] = useState<AccountLite[]>([])
  const [loading, setLoading] = useState(true)

  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [preview, setPreview] = useState<TransferApplyResult | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [r, accs] = await Promise.all([
        api.get<TransferRule[]>("/transfer-rules"),
        api.get<AccountLite[]>("/accounts"),
      ])
      setRules(r)
      setAccounts(accs)
    } catch (error) {
      console.error("Failed to load transfer rules", error)
      toast.error("Erreur lors du chargement des règles de virement")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const accountName = (id: number | null) => accounts.find((a) => a.id === id)?.name ?? "Compte inconnu"

  function openCreate() {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setFormOpen(true)
  }

  function openEdit(rule: TransferRule) {
    setEditingId(rule.id)
    setForm({
      source: rule.source_account_id.toString(),
      dest: rule.dest_account_id.toString(),
      pattern: rule.pattern ?? "",
      amount: rule.amount != null ? rule.amount.toString() : "",
      tolerance: rule.amount_tolerance_pct.toString(),
      days: rule.day_tolerance.toString(),
    })
    setFormOpen(true)
  }

  async function saveRule() {
    if (!form.source || !form.dest) {
      toast.error("Choisissez un compte source et un compte destination")
      return
    }
    const payload = {
      source_account_id: Number(form.source),
      dest_account_id: Number(form.dest),
      pattern: form.pattern.trim() || null,
      amount: form.amount ? parseFloat(form.amount.replace(",", ".")) : null,
      amount_tolerance_pct: parseFloat(form.tolerance.replace(",", ".")) || 1,
      day_tolerance: parseInt(form.days) || 5,
    }
    try {
      if (editingId === null) {
        await api.post("/transfer-rules", payload)
        toast.success("Règle créée")
      } else {
        await api.patch(`/transfer-rules/${editingId}`, payload)
        toast.success("Règle modifiée")
      }
      setFormOpen(false)
      setEditingId(null)
      setForm(EMPTY_FORM)
      loadData()
    } catch {
      toast.error(editingId === null ? "Impossible de créer la règle" : "Impossible de modifier la règle")
    }
  }

  async function toggleRule(rule: TransferRule) {
    try {
      await api.patch(`/transfer-rules/${rule.id}`, { is_active: !rule.is_active })
      loadData()
    } catch {
      toast.error("Échec de l'action")
    }
  }

  async function deleteRule(rule: TransferRule) {
    if (!(await confirm("Supprimer cette règle ? Les virements déjà liés restent liés."))) return
    try {
      await api.delete(`/transfer-rules/${rule.id}`)
      toast.success("Règle supprimée")
      loadData()
    } catch {
      toast.error("Échec de la suppression")
    }
  }

  async function previewCatchUp() {
    try {
      const result = await api.post<TransferApplyResult>("/transfer-rules/apply?dry_run=true", {})
      if (result.count === 0) {
        toast.info("Aucun virement à rattraper avec les règles actives")
        return
      }
      setPreview(result)
    } catch {
      toast.error("Échec de l'aperçu")
    }
  }

  async function applyCatchUp() {
    try {
      const result = await api.post<TransferApplyResult>("/transfer-rules/apply", {})
      toast.success(`${result.count} virement${result.count > 1 ? "s" : ""} lié${result.count > 1 ? "s" : ""}`)
      setPreview(null)
      loadData()
    } catch {
      toast.error("Échec du rattrapage")
    }
  }

  if (loading) return <div className="p-8 text-center text-slate-500">Chargement...</div>

  const accountSelect = (value: string, onChange: (v: string) => void, exclude?: string) => (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder="Choisir un compte" />
      </SelectTrigger>
      <SelectContent>
        {accounts
          .filter((a) => a.id.toString() !== exclude)
          .map((a) => (
            <SelectItem key={a.id} value={a.id.toString()}>
              {a.name}
            </SelectItem>
          ))}
      </SelectContent>
    </Select>
  )

  return (
    <div className="space-y-4 [&_input]:text-base md:[&_input]:text-sm">
      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
          <div>
            <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <ArrowRightLeft className="h-5 w-5 text-indigo-500" />
              Règles de virement
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Une règle relie automatiquement les sorties d'un compte aux entrées d'un autre (import, saisie, récurrences) dès que le couple est sans ambiguïté.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex">
            <Button variant="outline" size="sm" className="h-11 gap-2 px-2 sm:h-9 sm:px-3" onClick={previewCatchUp} disabled={rules.length === 0}>
              <History className="h-4 w-4" />
              Rattraper le passé
            </Button>
            <Button size="sm" className="h-11 gap-2 bg-indigo-600 px-2 hover:bg-indigo-700 sm:h-9 sm:px-3" onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Nouvelle règle
            </Button>
          </div>
        </div>

        <div className="grid gap-3">
          {rules.map((rule) => (
            <Card key={rule.id} className="border-slate-100 shadow-sm">
              <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <p className="flex flex-wrap items-center gap-x-2 font-bold text-slate-900">
                    <span className="break-words">{accountName(rule.source_account_id)}</span>
                    <ArrowRight className="h-4 w-4 shrink-0 text-indigo-400" />
                    <span className="break-words">{accountName(rule.dest_account_id)}</span>
                  </p>
                  <p className="text-xs text-slate-500">
                    {rule.pattern ? `Libellé contient « ${rule.pattern} » · ` : "Tout libellé · "}
                    {rule.amount ? `≈ ${formatCurrency(rule.amount)} · ` : "Tout montant · "}±{rule.amount_tolerance_pct} % · ±{rule.day_tolerance} j
                  </p>
                </div>
                <div className="flex shrink-0 items-center justify-between gap-1 border-t border-slate-100 pt-2 sm:justify-start sm:gap-3 sm:border-0 sm:pt-0">
                  <Switch checked={rule.is_active} onCheckedChange={() => toggleRule(rule)} />
                  <Button variant="ghost" size="sm" className="h-10 w-10 p-0 text-slate-400 md:h-8 md:w-8 hover:bg-indigo-50 hover:text-indigo-600" onClick={() => openEdit(rule)} aria-label="Modifier la règle">
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button aria-label="Supprimer" variant="ghost" size="sm" className="h-10 w-10 p-0 text-slate-400 md:h-8 md:w-8 hover:bg-red-50 hover:text-red-600" onClick={() => deleteRule(rule)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {rules.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-sm italic text-slate-400">
              Aucune règle. Créez-en une pour vos répartitions régulières (ex. Principal → Livret A).
            </div>
          )}
        </div>
      </section>

      {/* Création / édition de règle */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="[&_input]:text-base md:[&_input]:text-sm">
          <DialogHeader>
            <DialogTitle>{editingId === null ? "Nouvelle règle de virement" : "Modifier la règle de virement"}</DialogTitle>
            <DialogDescription>
              Les sorties du compte source seront reliées aux entrées du compte destination.
              {editingId !== null && " Les virements déjà liés ne changent pas : utilisez « Rattraper le passé » pour appliquer la règle modifiée à l'historique."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label>Compte source</Label>
                {accountSelect(form.source, (v) => setForm({ ...form, source: v }), form.dest)}
              </div>
              <div className="grid gap-2">
                <Label>Compte destination</Label>
                {accountSelect(form.dest, (v) => setForm({ ...form, dest: v }), form.source)}
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="rule-pattern">Le libellé de la sortie contient (optionnel)</Label>
              <Input id="rule-pattern" value={form.pattern} onChange={(e) => setForm({ ...form, pattern: e.target.value })} placeholder="ex. LIVRET" />
            </div>
            <div className="grid grid-cols-2 items-end gap-4 sm:grid-cols-3">
              <div className="col-span-2 grid gap-2 sm:col-span-1">
                <Label htmlFor="rule-amount">Montant (optionnel)</Label>
                <Input id="rule-amount" inputMode="decimal" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="500" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="rule-tol">Tolérance montant %</Label>
                <Input id="rule-tol" inputMode="decimal" value={form.tolerance} onChange={(e) => setForm({ ...form, tolerance: e.target.value })} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="rule-days">Tolérance jours</Label>
                <Input id="rule-days" inputMode="numeric" value={form.days} onChange={(e) => setForm({ ...form, days: e.target.value })} />
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="h-11 sm:h-10" onClick={() => setFormOpen(false)}>Annuler</Button>
            <Button className="h-11 bg-indigo-600 sm:h-10 hover:bg-indigo-700" onClick={saveRule}>{editingId === null ? "Créer la règle" : "Enregistrer"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Aperçu du rattrapage */}
      <Dialog open={preview !== null} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Rattraper le passé</DialogTitle>
            <DialogDescription>
              {preview?.count} virement{(preview?.count ?? 0) > 1 ? "s" : ""} seront liés sur tout l'historique. Les cas ambigus sont laissés en suggestions.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-80 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
            {preview?.pairs.map((p) => (
              <div key={`${p.sortie.id}-${p.entree.id}`} className="flex items-center justify-between gap-2 p-3 text-sm">
                <span className="hidden text-slate-500 sm:inline">{format(new Date(p.sortie.date), "dd/MM/yyyy")}</span>
                <span className="flex min-w-0 flex-wrap items-center gap-x-2 font-medium text-slate-800">
                  {accountName(p.sortie.account_id)}
                  <ArrowRight className="h-3 w-3 text-slate-400" />
                  {accountName(p.entree.account_id)}
                </span>
                <span className="whitespace-nowrap font-bold tabular-nums amount-blur">{formatCurrency(p.sortie.amount, p.sortie.currency)}</span>
              </div>
            ))}
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="h-11 sm:h-10" onClick={() => setPreview(null)}>Annuler</Button>
            <Button className="h-11 bg-indigo-600 sm:h-10 hover:bg-indigo-700" onClick={applyCatchUp}>Lier ces virements</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
