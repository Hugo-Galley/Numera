import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  RefreshCw,
  ShieldCheck,
  Wrench,
} from "lucide-react"
import { api } from "@/lib/api"
import { cn, formatCurrency } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

interface AuditIssue {
  id: string
  type: string
  severity: "low" | "medium" | "high"
  title: string
  description: string
  count: number
  amount?: number | null
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

function sampleLabel(sample: Record<string, any>) {
  if (sample.sortie && sample.entree) {
    return `${sample.sortie.merchant || "Sortie"} -> ${sample.entree.merchant || "Entree"}`
  }
  if (sample.name) return sample.name
  if (sample.merchant) return sample.merchant
  if (sample.date && sample.amount !== undefined) return `${sample.date} - ${formatCurrency(sample.amount, sample.currency || "EUR")}`
  return JSON.stringify(sample)
}

export default function Audit() {
  const navigate = useNavigate()
  const [data, setData] = useState<AuditData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadAudit() {
    setLoading(true)
    setError(null)
    try {
      const result = await api.get<AuditData>("/analytics/audit")
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit indisponible")
    } finally {
      setLoading(false)
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
      <div className="space-y-4">
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
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-slate-900" />
            <h1 className="text-3xl font-black tracking-tight text-slate-900">Audit des donnees</h1>
          </div>
          <p className="text-sm text-slate-500">
            Controle les incoherences qui peuvent fausser les soldes, budgets et analyses.
          </p>
        </div>
        <Button onClick={loadAudit} variant="outline" className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Relancer
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="md:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between">
              <span>Score de proprete</span>
              <span className={cn(
                "text-3xl font-black",
                score >= 80 ? "text-emerald-600" : score >= 55 ? "text-amber-600" : "text-rose-600"
              )}>
                {score}
              </span>
            </CardTitle>
            <CardDescription>
              {data.summary.total_transactions} transactions controlees sur {data.summary.active_accounts} comptes actifs.
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

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Alertes critiques</CardDescription>
            <CardTitle className="text-3xl font-black text-rose-600">{data.summary.high_count}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Actions proposees</CardDescription>
            <CardTitle className="text-3xl font-black text-slate-900">{data.summary.total_issues}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {sortedIssues.length === 0 ? (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-800">
              <CheckCircle2 className="h-5 w-5" />
              Donnees propres
            </CardTitle>
            <CardDescription className="text-emerald-700">
              Aucun probleme detecte sur les controles actuels.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4">
          {sortedIssues.map((issue) => (
            <Card key={issue.id} className="overflow-hidden">
              <CardContent className="p-0">
                <div className="flex flex-col gap-4 p-5 md:flex-row md:items-start md:justify-between">
                  <div className="flex min-w-0 gap-4">
                    <div className={cn("mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", issueIconClass[issue.severity])}>
                      <Wrench className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-black text-slate-900">{issue.title}</h2>
                        <Badge variant="outline" className={severityClass[issue.severity]}>
                          {severityLabel[issue.severity]}
                        </Badge>
                        <Badge variant="secondary">{issue.count}</Badge>
                      </div>
                      <p className="max-w-3xl text-sm leading-6 text-slate-600">{issue.description}</p>
                      {issue.samples.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {issue.samples.slice(0, 5).map((sample, index) => (
                            <span key={index} className="max-w-[260px] truncate rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
                              {sampleLabel(sample)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  {issue.action_url && (
                    <Button
                      variant={issue.severity === "high" ? "default" : "outline"}
                      className="shrink-0 gap-2"
                      onClick={() => navigate(issue.action_url || "/")}
                    >
                      {issue.action_label || "Ouvrir"}
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Database className="h-3.5 w-3.5" />
        Dernier controle : {new Date(data.summary.checked_at).toLocaleString("fr-FR")}
      </div>
    </div>
  )
}
