import { useCallback, useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { ArrowLeft, ChevronDown, ChevronRight, Landmark, Pencil, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { ErrorState } from "@/components/layout/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AccountLogo } from "@/components/ui/AccountLogo"
import { useSubmit } from "@/hooks/useSubmit"
import { api } from "@/lib/api"
import { todayLocal } from "@/lib/dates"
import { errorMessage, formatCurrency, formatRate } from "@/lib/utils"
import { useConfirm } from "@/providers/ConfirmProvider"

import { LoanDialog } from "./LoanDialog"
import {
  formatDateFr,
  formatMonths,
  LOAN_KIND_LABELS,
  PREPAYMENT_MODE_LABELS,
  type LoanSummary,
  type PrepaymentMode,
  type ScheduleRow,
  type SimulationResult,
} from "./types"

const toNumber = (value: string) => Number(value.replace(",", ".").replace(/\s/g, ""))

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

export function LoanView({ accountId }: { accountId: number }) {
  const navigate = useNavigate()
  const confirm = useConfirm()
  const [loan, setLoan] = useState<LoanSummary | null>(null)
  const [schedule, setSchedule] = useState<ScheduleRow[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [openYears, setOpenYears] = useState<Set<string>>(new Set())

  const [simAmount, setSimAmount] = useState("")
  const [simDate, setSimDate] = useState(todayLocal())
  const [simMode, setSimMode] = useState<PrepaymentMode>("reduce_duration")
  const [simulation, setSimulation] = useState<SimulationResult | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setFailed(false)
    try {
      const summary = await api.get<LoanSummary>(`/loans/by-account/${accountId}`)
      const rows = await api.get<ScheduleRow[]>(`/loans/${summary.id}/schedule`)
      setLoan(summary)
      setSchedule(rows)
    } catch (error) {
      console.error("Failed to load loan", error)
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [accountId])

  useEffect(() => { load() }, [load])

  const byYear = useMemo(() => {
    const groups = new Map<string, ScheduleRow[]>()
    for (const row of schedule) {
      const year = row.date.slice(0, 4)
      groups.set(year, [...(groups.get(year) ?? []), row])
    }
    return [...groups.entries()]
  }, [schedule])

  const chartData = useMemo(
    () => schedule.filter((row, i) => i % 3 === 0 || i === schedule.length - 1).map((row) => ({ date: row.date.slice(0, 7), remaining: row.remaining })),
    [schedule],
  )

  const [handleSimulate, simulating] = useSubmit(async () => {
    if (!loan) return
    const amount = toNumber(simAmount)
    if (!(amount > 0)) {
      toast.error("Indiquez un montant à rembourser.")
      return
    }
    try {
      setSimulation(await api.post<SimulationResult>(`/loans/${loan.id}/simulate-prepayment`, { amount, date: simDate, mode: simMode }))
    } catch (error) {
      toast.error(errorMessage(error, "Simulation impossible"))
    }
  })

  const [handleRecord, recording] = useSubmit(async () => {
    if (!loan) return
    const amount = toNumber(simAmount)
    if (!(amount > 0)) return
    if (!(await confirm(`Enregistrer un remboursement anticipé de ${formatCurrency(amount)} le ${formatDateFr(simDate)} ?`, { destructive: false, confirmLabel: "Enregistrer" }))) return
    try {
      await api.post(`/loans/${loan.id}/prepayments`, { amount, date: simDate, mode: simMode })
      toast.success("Remboursement anticipé enregistré")
      setSimulation(null)
      setSimAmount("")
      load()
    } catch (error) {
      toast.error(errorMessage(error, "Enregistrement impossible"))
    }
  })

  const deletePrepayment = async (id: number) => {
    if (!loan || !(await confirm("Supprimer ce remboursement anticipé ?"))) return
    try {
      await api.delete(`/loans/${loan.id}/prepayments/${id}`)
      toast.success("Remboursement anticipé supprimé")
      load()
    } catch (error) {
      toast.error(errorMessage(error, "Suppression impossible"))
    }
  }

  const deleteLoan = async () => {
    if (!loan || !(await confirm(`Supprimer le crédit « ${loan.name} » et son échéancier ? Cette action est définitive.`))) return
    try {
      await api.delete(`/loans/${loan.id}`)
      toast.success("Crédit supprimé")
      navigate("/accounts")
    } catch (error) {
      toast.error(errorMessage(error, "Suppression impossible"))
    }
  }

  if (loading && !loan) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
        <Skeleton className="h-64" />
      </div>
    )
  }
  if (failed || !loan) return <ErrorState message="Impossible de charger ce crédit." onRetry={load} />

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild aria-label="Retour aux comptes">
            <Link to="/accounts"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <AccountLogo accountId={loan.account_id} logo={loan.logo} className="h-9 w-9" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{loan.name}</h1>
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Landmark className="h-4 w-4" />
              <span>Crédit {LOAN_KIND_LABELS[loan.kind].toLowerCase()}</span>
              {loan.institution && <Badge variant="secondary">{loan.institution}</Badge>}
              <span>· {formatRate(loan.annual_rate_pct)} sur {formatMonths(loan.duration_months)}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="h-10" onClick={() => setEditOpen(true)}><Pencil className="mr-2 h-4 w-4" /> Modifier</Button>
          <Button variant="ghost" size="icon" className="h-10 w-10 text-rose-600 hover:text-rose-700" aria-label="Supprimer le crédit" onClick={deleteLoan}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Capital restant dû" value={formatCurrency(loan.remaining_principal)} hint={`sur ${formatCurrency(loan.principal)} empruntés`} />
        <Stat
          label="Mensualité"
          value={formatCurrency(loan.monthly_payment + loan.insurance_monthly)}
          hint={loan.insurance_monthly ? `dont ${formatCurrency(loan.insurance_monthly)} d'assurance` : "hors assurance"}
        />
        <Stat label="Fin du crédit" value={formatDateFr(loan.end_date)} />
        <Stat label="Coût total" value={formatCurrency(loan.total_cost)} hint={`${formatCurrency(loan.total_interest)} d'intérêts`} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Remboursé : {formatRate(loan.repaid_pct, 1)}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress value={loan.repaid_pct} className="h-2" />
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={40} />
                <YAxis tick={{ fontSize: 11 }} width={70} tickFormatter={(v) => formatCurrency(v).replace(/,\d+/, "")} />
                <Tooltip formatter={(v: number) => [formatCurrency(v), "Capital restant dû"]} labelFormatter={(l) => `Échéance ${l}`} />
                <Area type="monotone" dataKey="remaining" name="Capital restant dû" stroke="#e11d48" fill="#fecdd3" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Simuler un remboursement anticipé</CardTitle>
          <CardDescription>Rien n'est enregistré tant que vous ne validez pas.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-4 sm:items-end">
            <div className="grid gap-2">
              <Label htmlFor="sim-amount">Montant (€)</Label>
              <Input id="sim-amount" inputMode="decimal" placeholder="10000" value={simAmount} onChange={(e) => { setSimAmount(e.target.value); setSimulation(null) }} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="sim-date">Date</Label>
              <Input id="sim-date" type="date" value={simDate} onChange={(e) => { setSimDate(e.target.value); setSimulation(null) }} />
            </div>
            <div className="grid gap-2">
              <Label>Effet</Label>
              <Select value={simMode} onValueChange={(v) => { setSimMode(v as PrepaymentMode); setSimulation(null) }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(Object.keys(PREPAYMENT_MODE_LABELS) as PrepaymentMode[]).map((mode) => (
                    <SelectItem key={mode} value={mode}>{PREPAYMENT_MODE_LABELS[mode]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button className="h-10 bg-slate-900 text-white hover:bg-slate-800" onClick={() => handleSimulate()} disabled={simulating}>
              {simulating ? "Calcul…" : "Simuler"}
            </Button>
          </div>
          {simulation && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm">
              <p className="text-base font-semibold text-emerald-800">
                {formatCurrency(simulation.interest_saved)} d'intérêts économisés
              </p>
              <ul className="mt-2 space-y-1 text-slate-700">
                {simMode === "reduce_duration" ? (
                  <li>Fin du crédit le {formatDateFr(simulation.new_end_date)}, soit {formatMonths(simulation.months_saved)} plus tôt.</li>
                ) : (
                  <li>Nouvelle mensualité : {formatCurrency(simulation.new_payment)} (hors assurance).</li>
                )}
                <li>
                  Indemnités de remboursement anticipé : au plus {formatCurrency(simulation.max_penalty)} (plafond légal ; votre contrat peut prévoir moins ou rien).
                </li>
              </ul>
              <Button variant="outline" className="mt-3 h-10" onClick={() => handleRecord()} disabled={recording}>
                {recording ? "Enregistrement…" : "J'ai effectué ce remboursement"}
              </Button>
            </div>
          )}
          {loan.prepayments.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Remboursements anticipés effectués</p>
              {loan.prepayments.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm">
                  <span>{formatDateFr(p.date)} · {formatCurrency(p.amount)} · {PREPAYMENT_MODE_LABELS[p.mode].toLowerCase()}</span>
                  <Button variant="ghost" size="icon" className="h-9 w-9 text-rose-600" aria-label="Supprimer" onClick={() => deletePrepayment(p.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tableau d'amortissement</CardTitle>
          <CardDescription>{schedule.length} échéances. Touchez une année pour le détail.</CardDescription>
        </CardHeader>
        <CardContent className="px-2 sm:px-6">
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Échéance</TableHead>
                  <TableHead className="text-right">Mensualité</TableHead>
                  <TableHead className="text-right">Intérêts</TableHead>
                  <TableHead className="text-right">Capital</TableHead>
                  <TableHead className="text-right">Restant dû</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {byYear.map(([year, rows]) => {
                  const open = openYears.has(year)
                  const toggle = () => setOpenYears((prev) => {
                    const next = new Set(prev)
                    if (next.has(year)) next.delete(year)
                    else next.add(year)
                    return next
                  })
                  const sum = (key: "payment" | "interest" | "principal") => rows.reduce((acc, r) => acc + r[key], 0)
                  return [
                    <TableRow key={year} className="cursor-pointer bg-slate-50 font-semibold hover:bg-slate-100" onClick={toggle}>
                      <TableCell>
                        <span className="flex items-center gap-1">
                          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          {year} <span className="font-normal text-muted-foreground">({rows.length})</span>
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{formatCurrency(sum("payment"))}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatCurrency(sum("interest"))}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatCurrency(sum("principal"))}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatCurrency(rows[rows.length - 1].remaining)}</TableCell>
                    </TableRow>,
                    ...(open ? rows.map((row) => (
                      <TableRow key={`${year}-${row.n}`}>
                        <TableCell className="pl-8 text-sm">
                          {formatDateFr(row.date)}
                          {row.prepayment > 0 && <Badge variant="secondary" className="ml-2">+ {formatCurrency(row.prepayment)} anticipé</Badge>}
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums">{formatCurrency(row.payment)}</TableCell>
                        <TableCell className="text-right text-sm tabular-nums">{formatCurrency(row.interest)}</TableCell>
                        <TableCell className="text-right text-sm tabular-nums">{formatCurrency(row.principal)}</TableCell>
                        <TableCell className="text-right text-sm tabular-nums">{formatCurrency(row.remaining)}</TableCell>
                      </TableRow>
                    )) : []),
                  ]
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <LoanDialog open={editOpen} onOpenChange={setEditOpen} loan={loan} onSaved={() => load()} />
    </div>
  )
}
