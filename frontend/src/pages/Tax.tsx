import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { AlertTriangle, CheckCircle2, FileText, Landmark, Settings2 } from "lucide-react"
import { api } from "@/lib/api"
import { formatCurrency, formatRate } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

type Kind = "pea" | "per" | "cto" | "assurance_vie" | "livret_a" | "livret_jeune" | "pee"

interface WrapperCard {
  kind: Kind
  account_id: number
  account_name: string
  opened_at: string | null
  current: number | null
  ceiling: number | null
  remaining: number | null
  used_pct: number | null
  age_years: number | null
  milestone_years: number | null
  milestone_reached: boolean | null
  estimated_tax_saving: number | null
  allowance: number | null
  total_contributed: number | null
  blocked: number | null
  available: number | null
  next_unlock_date: string | null
  alerts: string[]
}

interface TaxSettings {
  tmi_pct: number
  prior_year_pro_income: number
  household: "single" | "couple"
  gross_annual_salary: number
}

interface WrapperSuggestion {
  account_id: number
  account_name: string
  kind: Kind
}

interface TaxOverview {
  year: number
  settings: TaxSettings
  wrappers: WrapperCard[]
  suggestions: WrapperSuggestion[]
}

interface CtoYearRow {
  account_id: number
  account_name: string
  dividends_gross_eur: number
  dividends_net_eur: number
  withholding_eur: number
  realized_eur: number
  proceeds_eur: number
  sales: number
  unknown_cost_sales: number
}

interface AnnualReport {
  year: number
  pfu_rate_dividends: number
  pfu_rate_gains: number
  accounts: CtoYearRow[]
  box_2dc: number
  box_3vg: number
  box_3vh: number
  estimated_pfu_eur: number
  warnings: string[]
}

const KIND_LABELS: Record<Kind, string> = {
  pea: "PEA",
  per: "PER",
  cto: "CTO",
  assurance_vie: "Assurance-vie",
  livret_a: "Livret A",
  livret_jeune: "Livret Jeune",
  pee: "PEE",
}

const TMI_OPTIONS = [0, 11, 30, 41, 45]

function Money({ value }: { value: number }) {
  return <span className="amount-blur whitespace-nowrap tabular-nums">{formatCurrency(value)}</span>
}

function Gauge({ pct }: { pct: number }) {
  const color = pct > 100 ? "bg-rose-500" : pct > 90 ? "bg-amber-500" : "bg-emerald-500"
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  )
}

function WrapperCardView({ card }: { card: WrapperCard }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-start justify-between gap-3 text-base">
          <span className="min-w-0 break-words">{card.account_name}</span>
          <span className="shrink-0 pt-0.5 text-xs font-semibold uppercase tracking-wider text-slate-500">{KIND_LABELS[card.kind]}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {card.ceiling !== null && card.current !== null && (
          <div className="space-y-2">
            <Gauge pct={card.used_pct ?? 0} />
            <div className="flex flex-wrap justify-between gap-x-3">
              <span><Money value={card.current} /> sur <Money value={card.ceiling} /></span>
              <span className="text-slate-500">{formatRate(card.used_pct ?? 0, 1)}</span>
            </div>
            <div className="text-slate-600 dark:text-slate-300">
              Place restante : <strong><Money value={card.remaining ?? 0} /></strong>
            </div>
          </div>
        )}
        {card.milestone_years !== null && (
          <div className="flex items-center gap-2">
            {card.milestone_reached && <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
            {card.age_years !== null ? (
              <span>
                Ancienneté : {card.age_years.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} an(s) / {card.milestone_years} ans
                {card.milestone_reached ? " — atteint" : ""}
              </span>
            ) : (
              <span className="text-slate-500">Ancienneté inconnue (seuil : {card.milestone_years} ans)</span>
            )}
          </div>
        )}
        {card.estimated_tax_saving !== null && (
          <div>Économie d'impôt estimée : <strong><Money value={card.estimated_tax_saving} /></strong></div>
        )}
        {card.allowance !== null && (
          <div>Abattement annuel sur les gains de rachat : <strong><Money value={card.allowance} /></strong></div>
        )}
        {card.total_contributed !== null && (
          <div className="space-y-1">
            <div>Total versé : <strong><Money value={card.total_contributed} /></strong></div>
            <div>Disponible : <strong><Money value={card.available ?? 0} /></strong></div>
            <div>
              Bloqué (moins de 5 ans) : <strong><Money value={card.blocked ?? 0} /></strong>
              {card.next_unlock_date && (
                <span className="text-slate-500"> — prochain déblocage le {new Date(card.next_unlock_date).toLocaleDateString("fr-FR")}</span>
              )}
            </div>
          </div>
        )}
        {card.alerts.map((alert) => (
          <div key={alert} className="flex items-start gap-2 rounded-md bg-amber-50 p-2 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{alert}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export default function Tax() {
  const currentYear = new Date().getFullYear()
  const [overview, setOverview] = useState<TaxOverview | null>(null)
  const [report, setReport] = useState<AnnualReport | null>(null)
  const [year, setYear] = useState(currentYear)
  const [loadingOverview, setLoadingOverview] = useState(true)
  const [loadingReport, setLoadingReport] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [draft, setDraft] = useState<TaxSettings | null>(null)

  const loadOverview = async () => {
    try {
      const data = await api.get<TaxOverview>("/tax/overview")
      setOverview(data)
      setDraft(data.settings)
    } catch {
      toast.error("Impossible de charger les enveloppes fiscales")
    } finally {
      setLoadingOverview(false)
    }
  }

  useEffect(() => {
    loadOverview()
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoadingReport(true)
    api
      .get<AnnualReport>(`/tax/annual-report?year=${year}`)
      .then((data) => !cancelled && setReport(data))
      .catch(() => !cancelled && toast.error("Impossible de charger le récapitulatif annuel"))
      .finally(() => !cancelled && setLoadingReport(false))
    return () => {
      cancelled = true
    }
  }, [year])

  const saveSettings = async () => {
    if (!draft) return
    try {
      await api.patch("/tax/settings", draft)
      toast.success("Réglages enregistrés")
      await loadOverview()
    } catch {
      toast.error("Erreur lors de l'enregistrement des réglages")
    }
  }

  const applySuggestion = async (s: WrapperSuggestion) => {
    try {
      await api.patch(`/accounts/${s.account_id}`, { tax_wrapper: s.kind })
      toast.success(`${s.account_name} suivi comme ${KIND_LABELS[s.kind]}`)
      await loadOverview()
    } catch {
      toast.error("Impossible d'enregistrer l'enveloppe")
    }
  }

  const cards = (overview?.wrappers ?? []).filter((w) => w.kind !== "cto")
  const suggestions = overview?.suggestions ?? []
  const years = Array.from({ length: 6 }, (_, i) => currentYear - i)

  return (
    <div className="space-y-6 md:space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between sm:gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Fiscalité</h1>
          <p className="text-sm text-muted-foreground md:text-base">Plafonds, dates clés et déclaration de tes enveloppes.</p>
        </div>
        <Button variant="outline" className="h-11 w-full sm:h-10 sm:w-auto" onClick={() => setSettingsOpen((open) => !open)}>
          <Settings2 className="mr-2 h-4 w-4" /> Réglages
        </Button>
      </div>

      {settingsOpen && draft && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Réglages fiscaux</CardTitle>
            <CardDescription>Servent au calcul du plafond PER, de l'économie d'impôt et de l'abattement assurance-vie.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="grid gap-2">
              <Label htmlFor="tax-tmi">Tranche marginale (TMI)</Label>
              <Select value={String(draft.tmi_pct)} onValueChange={(v) => setDraft({ ...draft, tmi_pct: Number(v) })}>
                <SelectTrigger id="tax-tmi"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TMI_OPTIONS.map((t) => <SelectItem key={t} value={String(t)}>{t} %</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tax-income">Revenus professionnels de l'année précédente (€)</Label>
              <Input
                id="tax-income"
                type="number" inputMode="decimal"
                min={0}
                value={draft.prior_year_pro_income}
                onChange={(e) => setDraft({ ...draft, prior_year_pro_income: Number(e.target.value) || 0 })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tax-household">Foyer</Label>
              <Select value={draft.household} onValueChange={(v) => setDraft({ ...draft, household: v as TaxSettings["household"] })}>
                <SelectTrigger id="tax-household"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">Seul</SelectItem>
                  <SelectItem value="couple">Couple</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tax-gross">Salaire brut annuel (€), pour le plafond du PEE</Label>
              <Input
                id="tax-gross"
                type="number" inputMode="decimal"
                min={0}
                value={draft.gross_annual_salary}
                onChange={(e) => setDraft({ ...draft, gross_annual_salary: Number(e.target.value) || 0 })}
              />
            </div>
            <div className="md:col-span-3">
              <Button className="h-11 w-full sm:h-10 sm:w-auto" onClick={saveSettings}>Enregistrer</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Plafonds et dates clés</h2>
        {suggestions.length > 0 && (
          <Card className="border-amber-200 bg-amber-50/50">
            <CardContent className="space-y-3 p-4">
              <p className="text-sm text-slate-700">
                Ces comptes n'ont pas d'enveloppe fiscale : leurs plafonds et dates clés ne sont pas suivis.
              </p>
              {suggestions.map((s) => (
                <div key={s.account_id} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span className="text-sm">
                    <span className="font-semibold">{s.account_name}</span> — enveloppe probable : {KIND_LABELS[s.kind]}
                  </span>
                  <Button size="sm" variant="outline" className="h-10 sm:h-9" onClick={() => applySuggestion(s)}>
                    Suivre comme {KIND_LABELS[s.kind]}
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
        {loadingOverview ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-44" />
            <Skeleton className="h-44" />
          </div>
        ) : cards.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
              <Landmark className="h-8 w-8 text-slate-400" />
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Aucun compte n'a d'enveloppe fiscale. Renseigne l'enveloppe dans les paramètres d'un compte.
              </p>
              <Button asChild variant="outline" className="h-11 w-full sm:h-10 sm:w-auto"><Link to="/accounts">Aller aux comptes</Link></Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {cards.map((card) => <WrapperCardView key={card.account_id} card={card} />)}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-xl font-semibold"><FileText className="h-5 w-5" /> Déclaration</h2>
          <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
            <SelectTrigger className="w-32" aria-label="Année de déclaration"><SelectValue /></SelectTrigger>
            <SelectContent>
              {years.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        {loadingReport || !report ? (
          <Skeleton className="h-40" />
        ) : report.accounts.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-slate-600 dark:text-slate-300">
              Aucun compte CTO configuré.
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="space-y-4 pt-6">
              {report.warnings.map((warning) => (
                <div key={warning} className="flex items-start gap-2 rounded-md bg-amber-50 p-2 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{warning}</span>
                </div>
              ))}
              <ul className="space-y-2 md:hidden">
                {report.accounts.map((row) => (
                  <li key={row.account_id} className="rounded-lg border p-3 text-sm">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="min-w-0 break-words font-medium">{row.account_name}</span>
                      <span className="shrink-0 text-xs text-slate-500">{row.sales} cession{row.sales > 1 ? "s" : ""}</span>
                    </div>
                    <dl className="mt-2 grid grid-cols-2 gap-3 border-t pt-2 text-xs">
                      <div>
                        <dt className="text-slate-500">Dividendes bruts (2DC)</dt>
                        <dd className="mt-0.5 text-sm font-semibold"><Money value={row.dividends_gross_eur} /></dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Plus-values réalisées</dt>
                        <dd className="mt-0.5 text-sm font-semibold"><Money value={row.realized_eur} /></dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ul>
              <Table className="hidden md:table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Compte</TableHead>
                    <TableHead className="text-right">Dividendes bruts (2DC)</TableHead>
                    <TableHead className="text-right">Plus-values réalisées</TableHead>
                    <TableHead className="text-right">Cessions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.accounts.map((row) => (
                    <TableRow key={row.account_id}>
                      <TableCell className="font-medium">{row.account_name}</TableCell>
                      <TableCell className="text-right"><Money value={row.dividends_gross_eur} /></TableCell>
                      <TableCell className="text-right"><Money value={row.realized_eur} /></TableCell>
                      <TableCell className="text-right">{row.sales}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <dl className="grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
                <div><dt className="text-slate-500">Case 2DC (dividendes)</dt><dd className="text-lg font-semibold"><Money value={report.box_2dc} /></dd></div>
                <div><dt className="text-slate-500">Case 3VG (plus-values)</dt><dd className="text-lg font-semibold"><Money value={report.box_3vg} /></dd></div>
                <div><dt className="text-slate-500">Case 3VH (moins-values)</dt><dd className="text-lg font-semibold"><Money value={report.box_3vh} /></dd></div>
                <div className="col-span-2 lg:col-span-1">
                  <dt className="text-slate-500">
                    Impôt estimé (PFU {formatRate(report.pfu_rate_dividends * 100, 1)} dividendes, {formatRate(report.pfu_rate_gains * 100, 1)} plus-values)
                  </dt>
                  <dd className="text-lg font-semibold"><Money value={report.estimated_pfu_eur} /></dd>
                </div>
              </dl>
              <p className="text-xs text-slate-500">Estimation indicative : ne remplace pas ta déclaration.</p>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  )
}
