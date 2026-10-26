import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  Link2,
  RefreshCw,
  Save,
  ShieldCheck,
  ShoppingBag,
  Trash2,
  Wrench,
  Zap,
  LayoutList,
  Target,
  X,
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { cn, formatCurrency } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useConfirm } from "@/providers/ConfirmProvider"
import { toInputValue, toNaiveLocal } from "@/lib/dates"

interface Category {
  id: number
  name: string
  type: string
}

interface Transaction {
  id: number
  account_id: number
  date: string
  type: string
  merchant: string
  category_id: number | null
  amount: number
  currency: string
  note?: string | null
}

interface Account {
  id: number
  name: string
  currency: string
}

interface ActionItem {
  id: string
  type: "audit" | "budget" | "rule" | "subscription"
  severity: "low" | "medium" | "high"
  title: string
  description: string
  action_label?: string | null
  action_url?: string | null
  action_type: "link" | "modal_categorize" | "modal_rule" | "modal_snapshot" | "modal_merchant"
  metadata?: Record<string, any>
  samples: Array<Record<string, any>>
}

interface ActionCenterData {
  summary: {
    total_actions: number
    high_priority: number
    medium_priority: number
    low_priority: number
    checked_at: string
  }
  actions: ActionItem[]
}

interface IssueDetails {
  issue_id: string
  transactions?: Transaction[]
  duplicate_groups?: Array<{ key: string; count: number; transactions: Transaction[] }>
  transfer_pairs?: Array<{ sortie: Transaction; entree: Transaction }>
}

// Mêmes mots que les compteurs du haut (« Priorité haute / moyenne », « Suggestions »)
const severityLabel = {
  high: "Priorité haute",
  medium: "Priorité moyenne",
  low: "Suggestion",
}

const severityClass = {
  high: "border-rose-200 text-rose-600",
  medium: "border-amber-200 text-amber-600",
  low: "border-slate-200 text-slate-500",
}

const actionIconClass = {
  high: "text-rose-500",
  medium: "text-amber-500",
  low: "text-slate-400",
}

const actionTypeIcon = {
  audit: ShieldCheck,
  budget: Target,
  rule: Zap,
  subscription: RefreshCw,
  merchant: ShoppingBag,
}

const toDateTimeLocal = toInputValue

function sampleLabel(sample: Record<string, any>) {
  if (sample.sortie && sample.entree) {
    return `${sample.sortie.merchant || "Sortie"} -> ${sample.entree.merchant || "Entree"}`
  }
  if (sample.name) return sample.name
  if (sample.merchant) return sample.merchant
  if (sample.date && sample.amount !== undefined) return `${sample.date} - ${formatCurrency(sample.amount, sample.currency || "EUR")}`
  return JSON.stringify(sample)
}

function TransactionEditor({
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

function RuleCreatorModal({
  merchant,
  suggestedCategoryId,
  categories,
  onCreated,
  onClose,
}: {
  merchant: string
  suggestedCategoryId?: number
  categories: Category[]
  onCreated: () => void
  onClose: () => void
}) {
  const [draft, setDraft] = useState({
    pattern: merchant,
    category_id: suggestedCategoryId ? String(suggestedCategoryId) : "none",
  })
  const [saving, setSaving] = useState(false)

  async function create() {
    setSaving(true)
    try {
      await api.post("/categorization-rules", {
        pattern: draft.pattern.trim(),
        category_id: draft.category_id === "none" ? null : Number(draft.category_id),
        priority: 0,
      })
      toast.success("Règle créée")
      onCreated()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Création impossible")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="[&_input]:text-base md:[&_input]:text-sm">
        <DialogHeader>
          <DialogTitle>Créer une règle d'auto-catégorisation</DialogTitle>
          <DialogDescription>
            Automatisez la catégorisation pour les futures transactions de "{merchant}".
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">Mot-clé (Pattern)</p>
            <Input value={draft.pattern} onChange={(e) => setDraft({...draft, pattern: e.target.value})} />
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Catégorie cible</p>
            <Select value={draft.category_id} onValueChange={(v) => setDraft({...draft, category_id: v})}>
              <SelectTrigger>
                <SelectValue placeholder="Choisir une catégorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Aucune</SelectItem>
                {categories.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" className="h-11 sm:h-10" onClick={onClose}>Annuler</Button>
          <Button className="h-11 sm:h-10" onClick={create} disabled={saving}>
            {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            Créer la règle
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function MerchantCreatorModal({
  merchant,
  variants,
  categories,
  onCreated,
  onClose,
}: {
  merchant: string
  variants?: string[]
  categories: Category[]
  onCreated: () => void
  onClose: () => void
}) {
  const [draft, setDraft] = useState({
    name: merchant,
    category_id: "none",
  })
  const [saving, setSaving] = useState(false)

  async function create() {
    setSaving(true)
    try {
      await api.post("/merchants", {
        name: draft.name.trim(),
        category_id: draft.category_id === "none" ? null : Number(draft.category_id),
        // Toutes les écritures repérées par le Centre d'actions, pas seulement la plus fréquente
        aliases: variants?.length ? variants : [merchant]
      })
      toast.success("Marchand créé et normalisé")
      await api.post("/merchants/auto-normalize", {})
      onCreated()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Création impossible")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="[&_input]:text-base md:[&_input]:text-sm">
        <DialogHeader>
          <DialogTitle>Normaliser le marchand</DialogTitle>
          <DialogDescription>
            Créez un marchand canonique pour "{merchant}".
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">Nom canonique</p>
            <Input value={draft.name} onChange={(e) => setDraft({...draft, name: e.target.value})} />
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Catégorie par défaut</p>
            <Select value={draft.category_id} onValueChange={(v) => setDraft({...draft, category_id: v})}>
              <SelectTrigger>
                <SelectValue placeholder="Choisir une catégorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Aucune</SelectItem>
                {categories.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" className="h-11 sm:h-10" onClick={onClose}>Annuler</Button>
          <Button className="h-11 sm:h-10" onClick={create} disabled={saving}>
            {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            Créer et normaliser
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function ActionCenter() {
  const navigate = useNavigate()
  const [data, setData] = useState<ActionCenterData | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [details, setDetails] = useState<Record<string, IssueDetails>>({})
  const [activeActionId, setActiveActionId] = useState<string | null>(null)
  const [ruleMerchant, setRuleMerchant] = useState<{merchant: string, catId?: number} | null>(null)
  const [normMerchant, setNormMerchant] = useState<{ merchant: string; variants?: string[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingIssueId, setLoadingIssueId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadActions() {
    setLoading(true)
    setError(null)
    try {
      const [result, categoryRows, accountRows] = await Promise.all([
        api.get<ActionCenterData>("/analytics/actions"),
        api.get<Category[]>("/categories"),
        api.get<Account[]>("/accounts"),
      ])
      setData(result)
      setCategories(categoryRows || [])
      setAccounts(accountRows || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Données indisponibles")
    } finally {
      setLoading(false)
    }
  }

  async function dismissAction(e: React.MouseEvent, actionId: string) {
    e.stopPropagation()
    try {
      await api.post('/analytics/actions/dismiss', { id: actionId })
      setData(prev => prev ? {
        ...prev,
        actions: prev.actions.filter(a => a.id !== actionId)
      } : null)
      toast.success("Action masquée")
    } catch(err) {
      toast.error("Impossible de masquer l'action")
    }
  }

  async function handleAction(action: ActionItem) {
    if (action.action_type === "link" && action.action_url) {
      navigate(action.action_url)
      return
    }

    if (action.action_type === "modal_rule") {
      setRuleMerchant({ merchant: action.metadata?.merchant, catId: action.metadata?.suggested_category_id })
      return
    }

    if (action.action_type === "modal_merchant") {
      setNormMerchant({ merchant: action.metadata?.merchant, variants: action.metadata?.variants })
      return
    }

    if (action.action_type === "modal_categorize") {
      const issueId = action.metadata?.issue_id
      if (!issueId) return
      
      setActiveActionId(action.id)
      if (details[issueId]) return

      setLoadingIssueId(action.id)
      try {
        const result = await api.get<IssueDetails>(`/analytics/audit/${issueId}`)
        setDetails((prev) => ({ ...prev, [issueId]: result }))
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Chargement impossible")
      } finally {
        setLoadingIssueId(null)
      }
    }
  }

  const activeAction = data?.actions.find(a => a.id === activeActionId)
  const activeIssueId = activeAction?.metadata?.issue_id
  const detail = activeIssueId ? details[activeIssueId] : null

  async function refreshIssue(issueId: string) {
    const result = await api.get<IssueDetails>(`/analytics/audit/${issueId}`)
    setDetails((prev) => ({ ...prev, [issueId]: result }))
    await loadActions()
  }

  function updateTransactionInDetails(issueId: string, saved: Transaction) {
    setDetails((prev) => {
      const detail = prev[issueId]
      if (!detail) return prev
      return {
        ...prev,
        [issueId]: {
          ...detail,
          transactions: detail.transactions?.map((tx) => tx.id === saved.id ? saved : tx),
          duplicate_groups: detail.duplicate_groups?.map((group) => ({
            ...group,
            transactions: group.transactions.map((tx) => tx.id === saved.id ? saved : tx),
          })),
          transfer_pairs: detail.transfer_pairs?.map((pair) => ({
            sortie: pair.sortie.id === saved.id ? saved : pair.sortie,
            entree: pair.entree.id === saved.id ? saved : pair.entree,
          })),
        },
      }
    })
    loadActions()
  }

  function removeTransactionFromDetails(issueId: string, id: number) {
    setDetails((prev) => {
      const detail = prev[issueId]
      if (!detail) return prev
      return {
        ...prev,
        [issueId]: {
          ...detail,
          transactions: detail.transactions?.filter((tx) => tx.id !== id),
          duplicate_groups: detail.duplicate_groups
            ?.map((group) => ({ ...group, transactions: group.transactions.filter((tx) => tx.id !== id) }))
            .filter((group) => group.transactions.length > 1),
          transfer_pairs: detail.transfer_pairs?.filter((pair) => pair.sortie.id !== id && pair.entree.id !== id),
        },
      }
    })
    loadActions()
  }

  async function linkTransfer(sortieId: number, entreeId: number) {
    try {
      await api.post(`/transactions/${sortieId}/link/${entreeId}?type=regular`, {})
      toast.success("Transfert rapproché")
      if (activeIssueId) await refreshIssue(activeIssueId)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Rapprochement impossible")
    }
  }

  async function ignoreTransfer(sortieId: number) {
    try {
      await api.post(`/transactions/${sortieId}/ignore`, {})
      toast.success("Suggestion ignorée")
      if (activeIssueId) await refreshIssue(activeIssueId)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action impossible")
    }
  }

  async function ignoreDuplicate(transactions: Transaction[]) {
    try {
      await Promise.all(transactions.map((tx) => api.post(`/transactions/${tx.id}/ignore-duplicate`, {})))
      toast.success("Doublons ignorés")
      if (activeIssueId) await refreshIssue(activeIssueId)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action impossible")
    }
  }

  useEffect(() => {
    loadActions()
  }, [])

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-slate-500">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span className="text-sm font-medium">Analyse des actions...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-rose-200 bg-white p-6">
        <div className="mb-2 flex items-center gap-2 text-rose-600">
          <AlertTriangle className="h-5 w-5" />
          <h2 className="text-sm font-semibold">Centre d'actions indisponible</h2>
        </div>
        <p className="mb-4 text-sm text-slate-600">{error}</p>
        <Button onClick={loadActions} variant="outline" size="sm">Relancer l'analyse</Button>
      </div>
    )
  }

  if (!data) return null

  if (activeActionId && activeAction) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => setActiveActionId(null)} className="-ml-2 h-10 px-2 text-slate-500 md:h-8">
            <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
            Retour au centre d'actions
          </Button>
        </div>

        <div className="flex gap-3">
          <div className={cn("mt-0.5 shrink-0", actionIconClass[activeAction.severity])}>
            <Wrench className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <h1 className="text-lg font-semibold text-slate-900">{activeAction.title}</h1>
              <Badge variant="outline" className={cn("text-[10px] font-medium uppercase tracking-wider", severityClass[activeAction.severity])}>
                {severityLabel[activeAction.severity]}
              </Badge>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">{activeAction.description}</p>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-2 sm:p-4 md:p-6">
          {loadingIssueId === activeActionId && (
            <div className="flex h-40 items-center justify-center gap-3 text-slate-500">
              <RefreshCw className="h-5 w-5 animate-spin" />
              <span>Chargement des détails...</span>
            </div>
          )}

          {detail?.transactions && (
            <div className="space-y-3">
              {detail.transactions.map((tx) => (
                <TransactionEditor
                  key={tx.id}
                  tx={tx}
                  categories={categories}
                  accounts={accounts}
                  onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                />
              ))}
            </div>
          )}

          {detail?.duplicate_groups && (
            <div className="space-y-6">
              {detail.duplicate_groups.map((group) => (
                <div key={group.key} className="space-y-3">
                  <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                    <p className="text-sm font-bold text-slate-900">{group.count} transactions identiques détectées</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => ignoreDuplicate(group.transactions)}
                        className="h-10 text-[10px] font-bold uppercase tracking-wider sm:h-7"
                      >
                        Marquer comme OK
                      </Button>
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100">
                        Action requise
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-2 shadow-sm sm:p-3">
                    {group.transactions.map((tx) => (
                      <TransactionEditor
                        key={tx.id}
                        tx={tx}
                        categories={categories}
                        accounts={accounts}
                        onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                        onDeleted={(id) => activeIssueId && removeTransactionFromDetails(activeIssueId, id)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {detail?.transfer_pairs && (
            <div className="space-y-6">
              {detail.transfer_pairs.map((pair) => (
                <div key={`${pair.sortie.id}-${pair.entree.id}`} className="space-y-3">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between px-1">
                    <div>
                      <p className="text-sm font-bold text-slate-900">
                        {formatCurrency(pair.sortie.amount, pair.sortie.currency)} entre deux comptes
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-2 md:flex">
                      <Button size="sm" className="h-11 md:h-9" onClick={() => linkTransfer(pair.sortie.id, pair.entree.id)}>
                        <Link2 className="h-4 w-4" />
                        Rapprocher
                      </Button>
                      <Button size="sm" variant="outline" className="h-11 md:h-9" onClick={() => ignoreTransfer(pair.sortie.id)}>
                        Ignorer
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    <TransactionEditor
                      tx={pair.sortie}
                      categories={categories}
                      accounts={accounts}
                      onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                    />
                    <TransactionEditor
                      tx={pair.entree}
                      categories={categories}
                      accounts={accounts}
                      onSaved={(saved) => activeIssueId && updateTransactionInDetails(activeIssueId, saved)}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {detail && !detail.transactions?.length && !detail.duplicate_groups?.length && !detail.transfer_pairs?.length && (
            <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-slate-200 bg-white p-8 text-center">
              <CheckCircle2 className="h-10 w-10 text-emerald-500" />
              <div className="space-y-1">
                <p className="font-bold text-slate-900">Tout est corrigé !</p>
                <p className="text-sm text-slate-500">Il ne reste plus d'éléments à traiter pour cette action.</p>
              </div>
              <Button variant="outline" onClick={() => setActiveActionId(null)} className="mt-2">
                Retourner à la liste
              </Button>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <LayoutList className="h-5 w-5 text-slate-700" />
            <h1 className="text-xl font-semibold text-slate-900">Centre d'actions</h1>
          </div>
          <p className="text-sm text-slate-500">
            Une liste centralisée des tâches pour maintenir vos finances propres et sous contrôle.
          </p>
        </div>
        <Button onClick={loadActions} variant="outline" className="h-11 gap-2 md:h-10">
          <RefreshCw className="h-4 w-4" />
          Actualiser
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-2 sm:flex sm:flex-wrap sm:gap-4">
        <div className="flex min-w-0 flex-col gap-1 rounded-md border border-slate-200 bg-white p-3 sm:min-w-[140px]">
          <p className="text-xs font-medium text-slate-500">Priorité haute</p>
          <p className="text-xl font-semibold text-rose-600">{data.summary.high_priority}</p>
        </div>
        <div className="flex min-w-0 flex-col gap-1 rounded-md border border-slate-200 bg-white p-3 sm:min-w-[140px]">
          <p className="text-xs font-medium text-slate-500">Priorité moyenne</p>
          <p className="text-xl font-semibold text-amber-600">{data.summary.medium_priority}</p>
        </div>
        <div className="flex min-w-0 flex-col gap-1 rounded-md border border-slate-200 bg-white p-3 sm:min-w-[140px]">
          <p className="text-xs font-medium text-slate-500">Suggestions</p>
          <p className="text-xl font-semibold text-slate-700">{data.summary.low_priority}</p>
        </div>
      </div>

      {data.actions.length === 0 ? (
        <div className="rounded-md border border-slate-200 bg-white p-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
            <CheckCircle2 className="h-6 w-6 text-emerald-500" />
          </div>
          <h2 className="text-sm font-semibold text-slate-900">Tout est à jour</h2>
          <p className="mt-1 text-sm text-slate-500">
            Félicitations ! Aucune action requise pour le moment. Votre comptabilité est impeccable.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
          <div className="divide-y divide-slate-100">
            {data.actions.map((action) => {
              const Icon = actionTypeIcon[action.type] || Wrench

              return (
                <div 
                  key={action.id} 
                  className="group flex cursor-pointer flex-col gap-4 p-4 transition-colors hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
                  onClick={() => handleAction(action)}
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", actionIconClass[action.severity])} />
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <h2 className="text-sm font-semibold text-slate-900">{action.title}</h2>
                        <Badge variant="outline" className={cn("h-5 px-1.5 text-[9px] font-medium uppercase tracking-wider", severityClass[action.severity])}>
                          {severityLabel[action.severity]}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 line-clamp-2 sm:line-clamp-1">{action.description}</p>
                    </div>
                  </div>
                  <div className="flex w-full shrink-0 items-center gap-2 sm:w-auto sm:gap-3">
                    {action.samples.length > 0 && (
                      <div className="hidden gap-2 sm:flex">
                        {action.samples.slice(0, 1).map((sample, index) => (
                          <span key={index} className="max-w-[150px] truncate text-xs text-slate-400">
                            Ex: {sampleLabel(sample)}
                          </span>
                        ))}
                      </div>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-11 flex-1 justify-center bg-slate-100 text-xs font-medium group-hover:bg-slate-200/50 sm:h-8 sm:flex-none sm:bg-transparent"
                    >
                      {action.action_label || "Traiter"}
                      <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-11 w-11 text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors sm:h-8 sm:w-8"
                      onClick={(e) => dismissAction(e, action.id)}
                      title="Masquer cette action définitivement"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {ruleMerchant && (
        <RuleCreatorModal 
          merchant={ruleMerchant.merchant}
          suggestedCategoryId={ruleMerchant.catId}
          categories={categories}
          onCreated={loadActions}
          onClose={() => setRuleMerchant(null)}
        />
      )}

      {normMerchant && (
        <MerchantCreatorModal 
          merchant={normMerchant.merchant}
          variants={normMerchant.variants}
          categories={categories}
          onCreated={loadActions}
          onClose={() => setNormMerchant(null)}
        />
      )}

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Database className="h-3.5 w-3.5" />
        Dernière analyse : {new Date(data.summary.checked_at).toLocaleString("fr-FR")}
      </div>
    </div>
  )
}
