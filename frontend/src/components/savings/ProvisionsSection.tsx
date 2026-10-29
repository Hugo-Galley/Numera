import { AlertTriangle, CalendarClock, PiggyBank, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ErrorState } from "@/components/layout/ErrorState"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { errorMessage, formatCurrency } from "@/lib/utils"
import { toast } from "sonner"
import { todayLocal } from "@/lib/dates"
import { useCallback, useEffect, useState } from "react"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useSubmit } from "@/hooks/useSubmit"
import { INTERVALS, Provision, ProvisionCard } from "./ProvisionCard"

interface ProvisionSummary {
  monthly_total: number
  target_now_total: number
  behind_count: number
  accounts: { account_id: number; account_name: string; balance: number; target_now: number; gap: number }[]
}

interface Option {
  id: number
  name: string
  type?: string
  active?: boolean
}

const emptyForm = () => ({
  name: "",
  amount: "",
  interval_months: "12",
  due_date: todayLocal(),
  category_id: "none",
  account_id: "none",
  note: "",
})

export function ProvisionsSection() {
  const confirm = useConfirm()
  const [provisions, setProvisions] = useState<Provision[]>([])
  const [summary, setSummary] = useState<ProvisionSummary | null>(null)
  const [categories, setCategories] = useState<Option[]>([])
  const [accounts, setAccounts] = useState<Option[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Provision | null>(null)
  const [form, setForm] = useState(emptyForm)

  const load = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([
        api.get<Provision[]>("/provisions"),
        api.get<ProvisionSummary>("/provisions/summary"),
      ])
      setProvisions(list)
      setSummary(sum)
      setFailed(false)
    } catch {
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    Promise.all([api.get<Option[]>("/categories?include_archived=false"), api.get<Option[]>("/accounts")])
      .then(([cats, accs]) => {
        setCategories(cats.filter((c) => c.type !== "revenu"))
        setAccounts(accs.filter((a) => a.active !== false))
      })
      .catch(() => undefined)
  }, [load])

  const openCreate = () => {
    setEditing(null)
    setForm(emptyForm())
    setDialogOpen(true)
  }

  const openEdit = (p: Provision) => {
    setEditing(p)
    setForm({
      name: p.name,
      amount: String(p.amount),
      interval_months: String(p.interval_months),
      due_date: p.next_due,
      category_id: p.category_id ? String(p.category_id) : "none",
      account_id: p.account_id ? String(p.account_id) : "none",
      note: p.note ?? "",
    })
    setDialogOpen(true)
  }

  const [save, saving] = useSubmit(async () => {
    const amount = parseFloat(form.amount.replace(",", "."))
    if (!form.name.trim() || !(amount > 0) || !form.due_date) {
      toast.error("Nom, montant et date d'échéance sont requis")
      return
    }
    const payload = {
      name: form.name.trim(),
      amount,
      interval_months: Number(form.interval_months),
      due_date: form.due_date,
      category_id: form.category_id === "none" ? null : Number(form.category_id),
      account_id: form.account_id === "none" ? null : Number(form.account_id),
      note: form.note.trim() || null,
    }
    try {
      if (editing) await api.patch(`/provisions/${editing.id}`, payload)
      else await api.post("/provisions", payload)
      toast.success(editing ? "Provision mise à jour" : "Provision créée")
      setDialogOpen(false)
      load()
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de l'enregistrement"))
    }
  })

  const remove = async (p: Provision) => {
    if (!(await confirm(`Supprimer la provision « ${p.name} » ?`))) return
    try {
      await api.delete(`/provisions/${p.id}`)
      toast.success("Provision supprimée")
      load()
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de la suppression"))
    }
  }

  const toggleActive = async (p: Provision) => {
    try {
      await api.patch(`/provisions/${p.id}`, { active: !p.active })
      load()
    } catch (error) {
      toast.error(errorMessage(error, "Erreur lors de la mise à jour"))
    }
  }

  return (
    <section className="space-y-4 md:space-y-6">
      <div className="flex flex-col justify-between gap-3 border-b pb-3 sm:flex-row sm:items-center md:pb-2">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-5 w-5 text-slate-400" />
          <h2 className="text-xl font-bold text-slate-900">Provisions</h2>
          {summary && summary.monthly_total > 0 && (
            <span className="text-sm text-slate-500">· {formatCurrency(summary.monthly_total)} / mois à mettre de côté</span>
          )}
        </div>
        <Button className="h-11 w-full rounded-xl shadow-sm sm:h-10 sm:w-auto" onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nouvelle provision
        </Button>
      </div>

      {failed ? (
        <ErrorState message="Les provisions n'ont pas pu être chargées." onRetry={load} />
      ) : loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-40 rounded-2xl" />)}
        </div>
      ) : provisions.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <PiggyBank className="h-10 w-10 text-slate-300" />
            <p className="max-w-md text-sm text-slate-500">
              Taxe foncière, assurance, vacances… Déclarez vos grosses dépenses périodiques pour savoir combien
              mettre de côté chaque mois et vérifier que vous serez prêt à l'échéance.
            </p>
            <Button variant="outline" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Ajouter une provision
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {summary?.accounts.filter((a) => a.gap > 0).map((a) => (
            <div key={a.account_id} className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                {a.account_name} : {formatCurrency(a.balance)} sur le compte pour {formatCurrency(a.target_now)} qui
                devraient déjà être provisionnés. Il manque {formatCurrency(a.gap)}.
              </span>
            </div>
          ))}
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {provisions.map((p) => (
              <ProvisionCard key={p.id} provision={p} onEdit={() => openEdit(p)} onDelete={() => remove(p)} onToggle={() => toggleActive(p)} />
            ))}
          </div>
        </>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="rounded-2xl sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{editing ? "Modifier la provision" : "Nouvelle provision"}</DialogTitle>
            <DialogDescription>
              Rien n'est ajouté à vos transactions : la provision calcule seulement l'effort mensuel. Rattachez un
              compte d'épargne pour suivre ce qui est réellement de côté.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="prov-name">Nom</Label>
                <Input id="prov-name" placeholder="ex : Taxe foncière" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="prov-amount">Montant par échéance (€)</Label>
                <Input id="prov-amount" inputMode="decimal" placeholder="1200" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label>Périodicité</Label>
                <Select value={form.interval_months} onValueChange={(v) => setForm({ ...form, interval_months: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {INTERVALS.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="prov-due">Prochaine échéance</Label>
                <Input id="prov-due" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label>Catégorie de la dépense</Label>
                <Select value={form.category_id} onValueChange={(v) => setForm({ ...form, category_id: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Aucune</SelectItem>
                    {categories.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Compte de mise de côté</Label>
                <Select value={form.account_id} onValueChange={(v) => setForm({ ...form, account_id: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Aucun (non suivi)</SelectItem>
                    {accounts.map((a) => <SelectItem key={a.id} value={String(a.id)}>{a.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="prov-note">Note</Label>
              <Input id="prov-note" placeholder="facultatif" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Annuler</Button>
            <Button onClick={save} disabled={saving} className="bg-slate-900 text-white">Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
