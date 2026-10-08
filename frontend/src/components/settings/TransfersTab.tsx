import { useCallback, useEffect, useState } from "react"
import {
  AlertCircle,
  ArrowRight,
  ArrowRightLeft,
  Calendar,
  CheckCircle2,
  History,
  Link,
  Plus,
  Trash2,
  Unlink,
  Wallet,
} from "lucide-react"
import { format } from "date-fns"
import { fr } from "date-fns/locale"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
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
import type {
  AccountLite,
  LinkedTransfer,
  PotentialTransfer,
  TransferApplyResult,
  TransferRule,
} from "@/types/transfers"

const ORIGIN_LABEL: Record<string, string> = { manual: "Manuel", rule: "Règle", recurring: "Récurrence" }

const EMPTY_FORM = { source: "", dest: "", pattern: "", amount: "", tolerance: "1", days: "5" }

export function TransfersTab() {
  const [rules, setRules] = useState<TransferRule[]>([])
  const [potentials, setPotentials] = useState<PotentialTransfer[]>([])
  const [linked, setLinked] = useState<LinkedTransfer[]>([])
  const [accounts, setAccounts] = useState<AccountLite[]>([])
  const [loading, setLoading] = useState(true)

  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [preview, setPreview] = useState<TransferApplyResult | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [r, p, l, accs] = await Promise.all([
        api.get<TransferRule[]>("/transfer-rules"),
        api.get<PotentialTransfer[]>("/transactions/potential-transfers"),
        api.get<LinkedTransfer[]>("/transactions?is_transfer=true&type=Sortie&limit=1000"),
        api.get<AccountLite[]>("/accounts"),
      ])
      setRules(r)
      setPotentials(p)
      setLinked(l)
      setAccounts(accs)
    } catch (error) {
      console.error("Failed to load transfers", error)
      toast.error("Erreur lors du chargement des virements")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const accountName = (id: number | null) => accounts.find((a) => a.id === id)?.name ?? "Compte inconnu"

  async function createRule() {
    if (!form.source || !form.dest) {
      toast.error("Choisissez un compte source et un compte destination")
      return
    }
    try {
      await api.post("/transfer-rules", {
        source_account_id: Number(form.source),
        dest_account_id: Number(form.dest),
        pattern: form.pattern.trim() || null,
        amount: form.amount ? parseFloat(form.amount.replace(",", ".")) : null,
        amount_tolerance_pct: parseFloat(form.tolerance.replace(",", ".")) || 1,
        day_tolerance: parseInt(form.days) || 5,
      })
      toast.success("Règle créée")
      setFormOpen(false)
      setForm(EMPTY_FORM)
      loadData()
    } catch {
      toast.error("Impossible de créer la règle")
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
    if (!confirm("Supprimer cette règle ? Les virements déjà liés restent liés.")) return
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

  async function handleLink(p: PotentialTransfer) {
    try {
      await api.post(`/transactions/${p.sortie.id}/link/${p.entree.id}?type=${p.type}`, {})
      toast.success("Transactions liées avec succès")
      loadData()
    } catch {
      toast.error("Échec de la liaison")
    }
  }

  async function handleIgnore(p: PotentialTransfer) {
    try {
      await api.post(`/transactions/${p.sortie.id}/ignore?other_id=${p.entree.id}&type=${p.type}`, {})
      toast.success("Suggestion ignorée")
      loadData()
    } catch {
      toast.error("Échec de l'action")
    }
  }

  async function handleUnlink(id: number) {
    if (!confirm("Voulez-vous délier ces transactions ?")) return
    try {
      await api.post(`/transactions/${id}/unlink`, {})
      toast.success("Transactions déliées")
      loadData()
    } catch {
      toast.error("Échec de l'action")
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
    <div className="space-y-8">
      {/* Règles */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <ArrowRightLeft className="h-5 w-5 text-indigo-500" />
              Règles de virement
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Une règle relie automatiquement les sorties d'un compte aux entrées d'un autre (import, saisie, récurrences) dès que le couple est sans ambiguïté.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-2" onClick={previewCatchUp} disabled={rules.length === 0}>
              <History className="h-4 w-4" />
              Rattraper le passé
            </Button>
            <Button size="sm" className="gap-2 bg-indigo-600 hover:bg-indigo-700" onClick={() => setFormOpen(true)}>
              <Plus className="h-4 w-4" />
              Nouvelle règle
            </Button>
          </div>
        </div>

        <div className="grid gap-3">
          {rules.map((rule) => (
            <Card key={rule.id} className="border-slate-100 shadow-sm">
              <CardContent className="flex items-center justify-between gap-4 p-4">
                <div className="min-w-0 space-y-1">
                  <p className="flex items-center gap-2 font-bold text-slate-900">
                    {accountName(rule.source_account_id)}
                    <ArrowRight className="h-4 w-4 text-indigo-400" />
                    {accountName(rule.dest_account_id)}
                  </p>
                  <p className="text-xs text-slate-500">
                    {rule.pattern ? `Libellé contient « ${rule.pattern} » · ` : "Tout libellé · "}
                    {rule.amount ? `≈ ${formatCurrency(rule.amount)} · ` : "Tout montant · "}±{rule.amount_tolerance_pct} % · ±{rule.day_tolerance} j
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Switch checked={rule.is_active} onCheckedChange={() => toggleRule(rule)} />
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-400 hover:bg-red-50 hover:text-red-600" onClick={() => deleteRule(rule)}>
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

      {/* Suggestions */}
      <section className="space-y-4">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <AlertCircle className="h-5 w-5 text-amber-500" />
            Suggestions à confirmer
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Mouvements qui ressemblent à des virements internes mais qu'aucune règle n'a pu lier sans doute. Liez-les pour les exclure de vos dépenses réelles.
          </p>
        </div>

        <div className="grid gap-4">
          {potentials.map((pair) => (
            <Card key={`${pair.sortie.id}-${pair.type}-${pair.entree.id}`} className="overflow-hidden border-slate-100 shadow-sm transition-colors hover:border-indigo-200">
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex flex-1 items-center gap-6">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Wallet className="h-3 w-3 text-slate-400" />
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{accountName(pair.sortie.account_id)}</span>
                    </div>
                    <p className="font-bold text-slate-900">{pair.sortie.merchant}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <Calendar className="h-3 w-3" />
                      {format(new Date(pair.sortie.date), "dd MMMM yyyy", { locale: fr })}
                      <span className="font-medium text-red-500 amount-blur">-{formatCurrency(pair.sortie.amount, pair.sortie.currency)}</span>
                    </div>
                  </div>

                  <div className="flex flex-col items-center gap-1">
                    <ArrowRight className="h-5 w-5 text-indigo-400" />
                    {pair.ambiguous ? (
                      <Badge variant="outline" className="border-red-100 bg-red-50 px-1 py-0 text-[10px] text-red-700">Plusieurs choix</Badge>
                    ) : pair.confidence === "high" ? (
                      <Badge variant="outline" className="border-green-100 bg-green-50 px-1 py-0 text-[10px] text-green-700">Confiance haute</Badge>
                    ) : (
                      <Badge variant="outline" className="border-amber-100 bg-amber-50 px-1 py-0 text-[10px] text-amber-700">Moyenne</Badge>
                    )}
                  </div>

                  <div className="flex-1 space-y-1 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{accountName(pair.entree.account_id)}</span>
                      <Wallet className="h-3 w-3 text-slate-400" />
                    </div>
                    <p className="font-bold text-slate-900">{pair.entree.merchant || pair.entree.note || "Versement"}</p>
                    <div className="flex items-center justify-end gap-2 text-xs text-slate-400">
                      <span className="font-medium text-emerald-500 amount-blur">+{formatCurrency(pair.entree.amount, pair.entree.currency)}</span>
                      {format(new Date(pair.entree.date), "dd MMMM yyyy", { locale: fr })}
                      <Calendar className="h-3 w-3" />
                    </div>
                  </div>
                </div>

                <div className="ml-8 flex flex-col gap-2">
                  <Button size="sm" className="gap-2 bg-indigo-600 hover:bg-indigo-700" onClick={() => handleLink(pair)}>
                    <Link className="h-4 w-4" />
                    Lier
                  </Button>
                  <Button variant="ghost" size="sm" className="text-slate-400 hover:text-slate-600" onClick={() => handleIgnore(pair)}>
                    Ignorer
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}

          {potentials.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-12 text-center italic text-slate-400">
              Aucune suggestion en attente.
            </div>
          )}
        </div>
      </section>

      {/* Liés */}
      <section className="space-y-4">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            Virements liés
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Tous les virements rapprochés ({linked.length}). Délier un lien automatique empêche la règle de le recréer.
          </p>
        </div>

        <Card className="overflow-hidden border-slate-100 shadow-sm">
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              {linked.map((tx) => (
                <div key={tx.id} className="flex items-center justify-between p-4 transition-colors hover:bg-slate-50">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                      <ArrowRightLeft className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-bold text-slate-900">{tx.merchant}</p>
                      <div className="mt-0.5 flex items-center gap-2">
                        <span className="text-xs text-slate-500">{accountName(tx.account_id)}</span>
                        <ArrowRight className="h-3 w-3 text-slate-300" />
                        <span className="text-xs text-slate-500">{accountName(tx.linked_account_id)}</span>
                        <span className="mx-1 text-xs text-slate-300">•</span>
                        <span className="text-xs text-slate-400">{format(new Date(tx.date), "dd/MM/yyyy")}</span>
                        {tx.link_origin && (
                          <Badge variant="outline" className="px-1 py-0 text-[10px] text-slate-500">{ORIGIN_LABEL[tx.link_origin] ?? tx.link_origin}</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-bold text-slate-700 amount-blur">{formatCurrency(tx.amount, tx.currency)}</span>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-400 hover:bg-red-50 hover:text-red-600" onClick={() => handleUnlink(tx.id)}>
                      <Unlink className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
              {linked.length === 0 && (
                <div className="p-12 text-center italic text-slate-400">Aucun virement lié pour le moment.</div>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      <div className="flex gap-3 rounded-xl border border-blue-100 bg-blue-50 p-4">
        <AlertCircle className="h-5 w-5 shrink-0 text-blue-600" />
        <p className="text-xs leading-relaxed text-blue-800">
          Les virements liés sont exclus des KPI de <strong>revenus totaux</strong> et de <strong>dépenses réelles</strong> pour ne pas fausser votre taux d'épargne. Ils restent visibles dans le détail de chaque compte.
        </p>
      </div>

      {/* Nouvelle règle */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouvelle règle de virement</DialogTitle>
            <DialogDescription>Les sorties du compte source seront reliées aux entrées du compte destination.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid grid-cols-2 gap-4">
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
            <div className="grid grid-cols-3 gap-4">
              <div className="grid gap-2">
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
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)}>Annuler</Button>
            <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={createRule}>Créer la règle</Button>
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
              <div key={`${p.sortie.id}-${p.entree.id}`} className="flex items-center justify-between p-3 text-sm">
                <span className="text-slate-500">{format(new Date(p.sortie.date), "dd/MM/yyyy")}</span>
                <span className="flex items-center gap-2 font-medium text-slate-800">
                  {accountName(p.sortie.account_id)}
                  <ArrowRight className="h-3 w-3 text-slate-400" />
                  {accountName(p.entree.account_id)}
                </span>
                <span className="font-bold amount-blur">{formatCurrency(p.sortie.amount, p.sortie.currency)}</span>
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPreview(null)}>Annuler</Button>
            <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={applyCatchUp}>Lier ces virements</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
