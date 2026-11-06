import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
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
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useSubmit } from "@/hooks/useSubmit"
import { api } from "@/lib/api"
import { todayLocal } from "@/lib/dates"
import { errorMessage } from "@/lib/utils"

import { loanKindLabel, type LoanKind, type LoanSummary } from "./types"

const LOAN_KINDS: LoanKind[] = ["immobilier", "auto", "consommation", "etudiant", "autre"]

interface LoanDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Crédit à modifier ; absent = création */
  loan?: LoanSummary | null
  onSaved: (loan: LoanSummary) => void
}

interface FormState {
  name: string
  institution: string
  logo: string | null
  kind: LoanKind
  principal: string
  annual_rate_pct: string
  duration_years: string
  start_date: string
  insurance_monthly: string
}

const EMPTY: FormState = {
  name: "",
  institution: "",
  logo: null,
  kind: "immobilier",
  principal: "",
  annual_rate_pct: "",
  duration_years: "",
  start_date: "",
  insurance_monthly: "",
}

function fromLoan(loan: LoanSummary): FormState {
  return {
    name: loan.name,
    institution: loan.institution ?? "",
    logo: loan.logo,
    kind: loan.kind,
    principal: String(loan.principal).replace(".", ","),
    annual_rate_pct: String(loan.annual_rate_pct).replace(".", ","),
    duration_years: String(Math.round((loan.duration_months / 12) * 100) / 100).replace(".", ","),
    start_date: loan.start_date,
    insurance_monthly: loan.insurance_monthly ? String(loan.insurance_monthly).replace(".", ",") : "",
  }
}

const toNumber = (value: string) => Number(value.replace(",", ".").replace(/\s/g, ""))

export function LoanDialog({ open, onOpenChange, loan, onSaved }: LoanDialogProps) {
  const { t } = useTranslation("loans")
  const { t: tc } = useTranslation("common")
  const [form, setForm] = useState<FormState>(EMPTY)

  useEffect(() => {
    if (open) setForm(loan ? fromLoan(loan) : { ...EMPTY, start_date: todayLocal() })
  }, [open, loan])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }))

  const [handleSave, saving] = useSubmit(async () => {
    const principal = toNumber(form.principal)
    const rate = toNumber(form.annual_rate_pct || "0")
    const months = Math.round(toNumber(form.duration_years) * 12)
    if (!form.name.trim() || !(principal > 0) || !(months >= 1) || !(rate >= 0) || !form.start_date) {
      toast.error(t("dialog.missingFields"))
      return
    }
    const payload = {
      name: form.name.trim(),
      institution: form.institution.trim() || null,
      logo: form.logo,
      kind: form.kind,
      principal,
      annual_rate_pct: rate,
      duration_months: months,
      start_date: form.start_date,
      insurance_monthly: toNumber(form.insurance_monthly || "0") || 0,
    }
    try {
      const saved = loan
        ? await api.patch<LoanSummary>(`/loans/${loan.id}`, payload)
        : await api.post<LoanSummary>("/loans", payload)
      toast.success(loan ? t("dialog.updated") : t("dialog.added"))
      onSaved(saved)
      onOpenChange(false)
    } catch (error) {
      toast.error(errorMessage(error, t("dialog.saveError")))
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{loan ? t("dialog.editTitle") : t("dialog.newTitle")}</DialogTitle>
          <DialogDescription>
            {t("dialog.hint")}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="loan-name">{t("dialog.name")}</Label>
            <Input id="loan-name" placeholder={t("dialog.namePlaceholder")} value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="loan-institution">{t("dialog.bank")}</Label>
              <Input id="loan-institution" placeholder={t("dialog.bankPlaceholder")} value={form.institution} onChange={(e) => set("institution", e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label>{t("dialog.type")}</Label>
              <Select value={form.kind} onValueChange={(v) => set("kind", v as LoanKind)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LOAN_KINDS.map((kind) => (
                    <SelectItem key={kind} value={kind}>{loanKindLabel(kind)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid gap-2">
            <Label>{t("dialog.logo")}</Label>
            <LogoPicker value={form.logo} onChange={(logo) => set("logo", logo)} suggestFor={form.institution || form.name} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="loan-principal">{t("dialog.principal")}</Label>
              <Input id="loan-principal" inputMode="decimal" placeholder="200000" value={form.principal} onChange={(e) => set("principal", e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="loan-rate">{t("dialog.rate")}</Label>
              <Input id="loan-rate" inputMode="decimal" placeholder="3,6" value={form.annual_rate_pct} onChange={(e) => set("annual_rate_pct", e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="loan-duration">{t("dialog.duration")}</Label>
              <Input id="loan-duration" inputMode="decimal" placeholder="25" value={form.duration_years} onChange={(e) => set("duration_years", e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="loan-start">{t("dialog.firstPayment")}</Label>
              <Input id="loan-start" type="date" value={form.start_date} onChange={(e) => set("start_date", e.target.value)} />
            </div>
            <div className="grid gap-2 sm:col-span-2">
              <Label htmlFor="loan-insurance">{t("dialog.insurance")}</Label>
              <Input id="loan-insurance" inputMode="decimal" placeholder="0" value={form.insurance_monthly} onChange={(e) => set("insurance_monthly", e.target.value)} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>{tc("actions.cancel")}</Button>
          <Button onClick={() => handleSave()} disabled={saving} className="bg-slate-900 text-white hover:bg-slate-800">
            {saving ? tc("actions.saving") : tc("actions.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
