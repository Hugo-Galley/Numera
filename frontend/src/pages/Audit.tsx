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
  Trash2,
  Wrench,
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

interface AuditIssue {
  id: string
  type: string
  severity: "low" | "medium" | "high"
  title: string
  description: string
  count: number
  action_label?: string | null
  action_url?: string | null
  samples: Array<Record<string, any>>
}

interface AuditData {
  summary: {
    total_issues: number
    high_count: number
    medium_count: number
    low_count: number
    total_transactions: number
    active_accounts: number
    checked_at: string
  }
  issues: AuditIssue[]
}

interface IssueDetails {
  issue_id: string
  transactions?: Transaction[]
  duplicate_groups?: Array<{ key: string; count: number; transactions: Transaction[] }>
  transfer_pairs?: Array<{ sortie: Transaction; entree: Transaction }>
}

const severityLabel = {
  high: "Critique",
  medium: "A surveiller",
  low: "Nettoyage",
}

const severityClass = {
  high: "border-rose-200 bg-rose-50 text-rose-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  low: "border-slate-200 bg-slate-50 text-slate-600",
}

const issueIconClass = {
  high: "bg-rose-100 text-rose-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-slate-100 text-slate-600",
}

const editableIssueIds = new Set([
  "uncategorized-expenses",
  "missing-merchants",
  "duplicate-transactions",
  "unmatched-transfers",
])

function toDateTimeLocal(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return offsetDate.toISOString().slice(0, 16)
}

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
        date: draft.date ? new Date(draft.date).toISOString() : undefined,
        type: draft.type,
        merchant: draft.merchant.trim(),
        category_id: draft.category_id === "none" ? null : Number(draft.category_id),
        amount: Number(draft.amount),
        note: draft.note.trim() || null,
      })
      onSaved(saved)
      toast.success("Transaction enregistree")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sauvegarde impossible")
    } finally {
      setSaving(false)
    }
  }

  async function remove() {
    if (!confirm("Supprimer cette transaction ?")) return
    setSaving(true)
    try {
      await api.delete(`/transactions/${tx.id}`)
      onDeleted?.(tx.id)
      toast.success("Transaction supprimee")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Suppression impossible")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-md border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Mobile view: stack of fields */}
      <div className="flex flex-col p-3 gap-3 lg:hidden">
        <div className="flex items-center justify-between border-b pb-2">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Compte</p>
            <p className="truncate text-xs font-bold text-slate-700">{account?.name || `ID: ${tx.account_id}`}</p>
          </div>
          <Badge variant="outline" className="text-[10px]">{tx.currency}</Badge>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="mb-1 text-[10px] font-medium text-slate-400">Date et heure</p>
            <Input
              type="datetime-local"
              value={draft.date}
              onChange={(event) => setDraft({ ...draft, date: event.target.value })}
              className="h-9 text-xs"
            />
          </div>
          <div>
            <p className="mb-1 text-[10px] font-medium text-slate-400">Type</p>
            <Select value={draft.type} onValueChange={(value) => setDraft({ ...draft, type: value })}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Sortie">Sortie</SelectItem>
                <SelectItem value="Entree">Entree</SelectItem>
                <SelectItem value="Interets">Interets</SelectItem>
                <SelectItem value="Solde Initial">Solde Initial</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <p className="mb-1 text-[10px] font-medium text-slate-400">Marchand</p>
          <Input
            value={draft.merchant}
            onChange={(event) => setDraft({ ...draft, merchant: event.target.value })}
            placeholder="Marchand"
            className="h-9 text-xs"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="mb-1 text-[10px] font-medium text-slate-400">Catégorie</p>
            <Select value={draft.category_id} onValueChange={(value) => setDraft({ ...draft, category_id: value })}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Categorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sans categorie</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category.id} value={String(category.id)}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <p className="mb-1 text-[10px] font-medium text-slate-400">Montant</p>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={draft.amount}
              onChange={(event) => setDraft({ ...draft, amount: event.target.value })}
              className="h-9 text-xs font-bold"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t pt-3">
          {onDeleted && (
            <Button type="button" variant="outline" size="icon" onClick={remove} disabled={saving} className="h-9 w-9 text-rose-500 hover:bg-rose-50 hover:text-rose-600">
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          <Button type="button" size="sm" onClick={save} disabled={saving || !draft.merchant.trim() || Number(draft.amount) <= 0} className="h-9 shadow-sm flex-1">
            {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Enregistrer
          </Button>
        </div>
      </div>

      {/* Desktop view: horizontal scrollable grid */}
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
                <SelectItem value="Entree">Entree</SelectItem>
                <SelectItem value="Interets">Interets</SelectItem>
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
                <SelectValue placeholder="Categorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sans categorie</SelectItem>
                {categories.map((category) => (
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
                type="number"
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
              <Button type="button" variant="outline" size="icon" onClick={remove} disabled={saving} className="h-9 w-9 text-rose-500 hover:bg-rose-50 hover:text-rose-600">
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

export default function Audit() {
  const navigate = useNavigate()
  const [data, setData] = useState<AuditData | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [details, setDetails] = useState<Record<string, IssueDetails>>({})
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingIssueId, setLoadingIssueId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadAudit() {
    setLoading(true)
    setError(null)
    try {
      const [result, categoryRows, accountRows] = await Promise.all([
        api.get<AuditData>("/analytics/audit"),
        api.get<Category[]>("/categories"),
        api.get<Account[]>("/accounts"),
      ])
      setData(result)
      setCategories(categoryRows || [])
      setAccounts(accountRows || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit indisponible")
    } finally {
      setLoading(false)
    }
  }

  async function openIssue(issueId: string) {
    const issue = data?.issues.find((i) => i.id === issueId)
    if (!issue) return

    if (!editableIssueIds.has(issue.id)) {
      if (issue.action_url) navigate(issue.action_url)
      return
    }

    setActiveIssueId(issue.id)
    if (details[issue.id]) return

    setLoadingIssueId(issue.id)
    try {
      const result = await api.get<IssueDetails>(`/analytics/audit/${issue.id}`)
      setDetails((prev) => ({ ...prev, [issue.id]: result }))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Chargement impossible")
    } finally {
      setLoadingIssueId(null)
    }
  }

  async function refreshIssue(issueId: string) {
    const result = await api.get<IssueDetails>(`/analytics/audit/${issueId}`)
    setDetails((prev) => ({ ...prev, [issueId]: result }))
    await loadAudit()
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
    loadAudit()
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
    loadAudit()
  }

  async function linkTransfer(sortieId: number, entreeId: number) {
    try {
      await api.post(`/transactions/${sortieId}/link/${entreeId}?type=regular`, {})
      toast.success("Transfert rapproche")
      await refreshIssue("unmatched-transfers")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Rapprochement impossible")
    }
  }

  async function ignoreTransfer(sortieId: number) {
    try {
      await api.post(`/transactions/${sortieId}/ignore`, {})
      toast.success("Suggestion ignoree")
      await refreshIssue("unmatched-transfers")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action impossible")
    }
  }

  async function ignoreDuplicate(transactions: Transaction[]) {
    try {
      await Promise.all(transactions.map((tx) => api.post(`/transactions/${tx.id}/ignore-duplicate`, {})))
      toast.success("Doublons ignores")
      await refreshIssue("duplicate-transactions")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action impossible")
    }
  }

  useEffect(() => {
    loadAudit()
  }, [])

  const score = useMemo(() => {
    if (!data) return 0
    const penalty = data.summary.high_count * 28 + data.summary.medium_count * 14 + data.summary.low_count * 5
    return Math.max(0, Math.min(100, 100 - penalty))
  }, [data])

  const sortedIssues = useMemo(() => {
    const priority = { high: 0, medium: 1, low: 2 }
    return [...(data?.issues || [])].sort((a, b) => priority[a.severity] - priority[b.severity])
  }, [data])

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-slate-500">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span className="text-sm font-medium">Analyse des donnees...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-rose-200 bg-rose-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-rose-800">
            <AlertTriangle className="h-5 w-5" />
            Audit indisponible
          </CardTitle>
          <CardDescription className="text-rose-700">{error}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={loadAudit} variant="outline">Relancer l'audit</Button>
        </CardContent>
      </Card>
    )
  }

  if (!data) return null

  if (activeIssueId) {
    const issue = data.issues.find((i) => i.id === activeIssueId)
    const detail = details[activeIssueId]

    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => setActiveIssueId(null)} className="-ml-2 h-8 px-2 text-slate-500">
            <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
            Retour à l'audit
          </Button>
        </div>

        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="flex gap-4">
            <div className={cn("mt-1 flex h-12 w-12 shrink-0 items-center justify-center rounded-lg", issueIconClass[issue?.severity || "low"])}>
              <Wrench className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-slate-900">{issue?.title}</h1>
                <Badge variant="outline" className={severityClass[issue?.severity || "low"]}>
                  {severityLabel[issue?.severity || "low"]}
                </Badge>
              </div>
              <p className="mt-1 max-w-2xl text-slate-600">{issue?.description}</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 md:p-6">
          {loadingIssueId === activeIssueId && (
            <div className="flex h-40 items-center justify-center gap-3 text-slate-500">
              <RefreshCw className="h-5 w-5 animate-spin" />
              <span>Chargement des transactions...</span>
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
                  onSaved={(saved) => updateTransactionInDetails(activeIssueId, saved)}
                />
              ))}
            </div>
          )}

          {detail?.duplicate_groups && (
            <div className="space-y-6">
              {detail.duplicate_groups.map((group) => (
                <div key={group.key} className="space-y-3">
                  <div className="flex items-center justify-between gap-3 px-1">
                    <p className="text-sm font-bold text-slate-900">{group.count} transactions identiques détectées</p>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => ignoreDuplicate(group.transactions)}
                        className="h-7 text-[10px] font-bold uppercase tracking-wider"
                      >
                        Marquer comme OK
                      </Button>
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100">
                        Action requise
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    {group.transactions.map((tx) => (
                      <TransactionEditor
                        key={tx.id}
                        tx={tx}
                        categories={categories}
                        accounts={accounts}
                        onSaved={(saved) => updateTransactionInDetails(activeIssueId, saved)}
                        onDeleted={(id) => removeTransactionFromDetails(activeIssueId, id)}
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
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => linkTransfer(pair.sortie.id, pair.entree.id)}>
                        <Link2 className="h-4 w-4" />
                        Rapprocher comme transfert
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => ignoreTransfer(pair.sortie.id)}>
                        Ignorer cette suggestion
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    <TransactionEditor
                      tx={pair.sortie}
                      categories={categories}
                      accounts={accounts}
                      onSaved={(saved) => updateTransactionInDetails(activeIssueId, saved)}
                    />
                    <TransactionEditor
                      tx={pair.entree}
                      categories={categories}
                      accounts={accounts}
                      onSaved={(saved) => updateTransactionInDetails(activeIssueId, saved)}
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
                <p className="text-sm text-slate-500">Il ne reste plus de transactions problématiques pour ce contrôle.</p>
              </div>
              <Button variant="outline" onClick={() => setActiveIssueId(null)} className="mt-2">
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
          <div className="mb-2 flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-slate-900" />
            <h1 className="text-3xl font-black tracking-tight text-slate-900">Audit des donnees</h1>
          </div>
          <p className="text-sm text-slate-500">
            Corrige les incoherences qui peuvent fausser les soldes, budgets et analyses.
          </p>
        </div>
        <Button onClick={loadAudit} variant="outline" className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Relancer l'analyse
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="md:col-span-2 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between">
              <span>Score de santé des données</span>
              <span className={cn(
                "text-3xl font-black",
                score >= 80 ? "text-emerald-600" : score >= 55 ? "text-amber-600" : "text-rose-600"
              )}>
                {score}%
              </span>
            </CardTitle>
            <CardDescription>
              {data.summary.total_transactions} transactions contrôlées sur {data.summary.active_accounts} comptes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress
              value={score}
              className="h-3 bg-slate-100"
              indicatorClassName={score >= 80 ? "bg-emerald-500" : score >= 55 ? "bg-amber-500" : "bg-rose-500"}
            />
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription>Alertes critiques</CardDescription>
            <CardTitle className="text-3xl font-black text-rose-600">{data.summary.high_count}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription>Actions en attente</CardDescription>
            <CardTitle className="text-3xl font-black text-slate-900">{data.summary.total_issues}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {sortedIssues.length === 0 ? (
        <Card className="border-emerald-200 bg-emerald-50 shadow-none">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-800">
              <CheckCircle2 className="h-5 w-5" />
              Donnees propres
            </CardTitle>
            <CardDescription className="text-emerald-700">
              Aucun probleme detecte sur les controles actuels. Votre comptabilité est saine.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4">
          {sortedIssues.map((issue) => {
            const isEditable = editableIssueIds.has(issue.id)

            return (
              <Card 
                key={issue.id} 
                className={cn(
                  "overflow-hidden transition-all hover:shadow-md cursor-pointer",
                  isEditable ? "hover:border-slate-400" : ""
                )}
                onClick={() => openIssue(issue.id)}
              >
                <CardContent className="p-0">
                  <div className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
                    <div className="flex min-w-0 gap-4">
                      <div className={cn("mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-md", issueIconClass[issue.severity])}>
                        <Wrench className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="text-lg font-black text-slate-900">{issue.title}</h2>
                          <Badge variant="outline" className={cn("text-[10px] uppercase tracking-wider font-bold", severityClass[issue.severity])}>
                            {severityLabel[issue.severity]}
                          </Badge>
                          <Badge variant="secondary" className="bg-slate-100 text-slate-600">{issue.count}</Badge>
                        </div>
                        <p className="max-w-3xl text-sm text-slate-600">{issue.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {issue.samples.length > 0 && (
                        <div className="hidden flex-wrap gap-2 md:flex">
                          {issue.samples.slice(0, 2).map((sample, index) => (
                            <span key={index} className="max-w-[180px] truncate rounded border border-slate-100 bg-slate-50/50 px-2 py-0.5 text-[10px] font-medium text-slate-400">
                              {sampleLabel(sample)}
                            </span>
                          ))}
                        </div>
                      )}
                      <Button
                        variant={issue.severity === "high" && isEditable ? "default" : "outline"}
                        className="gap-2"
                        size="sm"
                      >
                        {isEditable ? "Corriger" : (issue.action_label || "Voir")}
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Database className="h-3.5 w-3.5" />
        Dernier contrôle automatique : {new Date(data.summary.checked_at).toLocaleString("fr-FR")}
      </div>
    </div>
  )
}
