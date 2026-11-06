import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useSubmit } from "@/hooks/useSubmit"
import { api } from "@/lib/api"
import { errorMessage } from "@/lib/utils"
import type { Benefit } from "./BenefitsSection"

export interface AccountOption {
  id: number
  name: string
}

// Préréglages : remplissent organisme, texte du libellé et déclaration
const PRESETS = {
  prime: { name: "Prime d'activité", organization: "CAF", match_pattern: "CAF", declaration_interval_months: "3" },
  apl: { name: "APL", organization: "CAF", match_pattern: "CAF", declaration_interval_months: "none" },
  other: { name: "", organization: "", match_pattern: "", declaration_interval_months: "none" },
}

const emptyForm = () => ({
  name: "",
  organization: "",
  amount: "",
  payment_day: "5",
  match_pattern: "",
  account_id: "none",
  start_date: "",
  declaration_interval_months: "none",
  next_declaration_date: "",
  note: "",
  logo: null as string | null,
  auto_generate: true,
})

type Form = ReturnType<typeof emptyForm>

const formFrom = (b: Benefit): Form => ({
  name: b.name,
  organization: b.organization,
  amount: String(b.amount),
  payment_day: String(b.payment_day),
  match_pattern: b.match_pattern,
  account_id: b.account_id ? String(b.account_id) : "none",
  start_date: b.start_date ?? "",
  declaration_interval_months: b.declaration_interval_months ? String(b.declaration_interval_months) : "none",
  next_declaration_date: b.next_declaration_date ?? "",
  note: b.note ?? "",
  logo: b.logo,
  auto_generate: b.auto_generate,
})

interface Props {
  open: boolean
  editing: Benefit | null
  accounts: AccountOption[]
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}

export function BenefitDialog({ open, editing, accounts, onOpenChange, onSaved }: Props) {
  const { t } = useTranslation("recurring")
  const [form, setForm] = useState<Form>(emptyForm)
  const set = (patch: Partial<Form>) => setForm((f) => ({ ...f, ...patch }))

  useEffect(() => {
    if (open) setForm(editing ? formFrom(editing) : emptyForm())
  }, [open, editing])

  const [save, saving] = useSubmit(async () => {
    const amount = parseFloat(form.amount.replace(",", "."))
    const hasDeclaration = form.declaration_interval_months !== "none"
    if (!form.name.trim() || !form.organization.trim() || !(amount > 0) || form.match_pattern.trim().length < 2) {
      toast.error(t("benefitDialog.nomOrganismeMontantEtTexte"))
      return
    }
    if (hasDeclaration && !form.next_declaration_date) {
      toast.error(t("benefitDialog.indiquezLaDateDeLa"))
      return
    }
    if (form.auto_generate && form.account_id === "none") {
      toast.error(t("benefitDialog.choisissezLeCompteDeReception"))
      return
    }
    const payload = {
      name: form.name.trim(),
      organization: form.organization.trim(),
      amount,
      payment_day: Math.min(31, Math.max(1, Number(form.payment_day) || 5)),
      match_pattern: form.match_pattern.trim(),
      account_id: form.account_id === "none" ? null : Number(form.account_id),
      start_date: form.start_date || null,
      declaration_interval_months: hasDeclaration ? Number(form.declaration_interval_months) : null,
      next_declaration_date: hasDeclaration ? form.next_declaration_date : null,
      note: form.note.trim() || null,
      logo: form.logo,
      auto_generate: form.auto_generate,
    }
    try {
      if (editing) await api.patch(`/benefits/${editing.id}`, payload)
      else await api.post("/benefits", payload)
      toast.success(editing ? t("benefitDialog.aideMiseAJour") : t("benefitDialog.aideAjoutee"))
      onOpenChange(false)
      onSaved()
    } catch (error) {
      toast.error(errorMessage(error, t("benefitDialog.erreurLorsDeLEnregistrement")))
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto rounded-2xl sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle>{editing ? t("benefitDialog.modifierLAide") : t("benefitDialog.nouvelleAide")}</DialogTitle>
          <DialogDescription>
            {t("benefitDialog.rienNEstAjouteA")}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          {!editing && (
            <div className="flex flex-wrap gap-2">
              {(["prime", "apl", "other"] as const).map((key) => (
                <Button key={key} type="button" variant="outline" size="sm" className="h-10 rounded-full md:h-8" onClick={() => set(PRESETS[key])}>
                  {key === "other" ? t("benefitDialog.autreAide") : PRESETS[key].name}
                </Button>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field id="ben-name" label={t("benefitDialog.nom")} placeholder={t("benefitDialog.exPrimeDActivite")} value={form.name} onChange={(v) => set({ name: v })} />
            <Field id="ben-org" label={t("benefitDialog.organisme")} placeholder={t("benefitDialog.cafCpamMsa")} value={form.organization} onChange={(v) => set({ organization: v })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field id="ben-amount" label={t("benefitDialog.montantMensuel")} placeholder="250" inputMode="decimal" value={form.amount} onChange={(v) => set({ amount: v })} />
            <Field id="ben-day" label={t("benefitDialog.jourDeVersement")} placeholder="5" inputMode="numeric" value={form.payment_day} onChange={(v) => set({ payment_day: v })} />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field id="ben-pattern" label={t("benefitDialog.texteDuLibelleBancaire")} placeholder={t("benefitDialog.exCaf")} value={form.match_pattern} onChange={(v) => set({ match_pattern: v })} />
            <div className="grid gap-2">
              <Label>{t("benefitDialog.compteDeReception")}</Label>
              <Select value={form.account_id} onValueChange={(v) => set({ account_id: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t("benefitDialog.tousLesComptes")}</SelectItem>
                  {accounts.map((a) => <SelectItem key={a.id} value={String(a.id)}>{a.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label>{t("benefitDialog.declaration")}</Label>
              <Select value={form.declaration_interval_months} onValueChange={(v) => set({ declaration_interval_months: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t("benefitDialog.aucune")}</SelectItem>
                  <SelectItem value="1">{t("benefitDialog.mensuelle")}</SelectItem>
                  <SelectItem value="3">{t("benefitDialog.trimestrielle")}</SelectItem>
                  <SelectItem value="12">{t("benefitDialog.annuelle")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.declaration_interval_months !== "none" && (
              <Field id="ben-decl" label={t("benefitDialog.prochaineDeclaration")} type="date" value={form.next_declaration_date} onChange={(v) => set({ next_declaration_date: v })} />
            )}
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="ben-generate" checked={form.auto_generate} onCheckedChange={(v) => set({ auto_generate: v === true })} />
            <Label htmlFor="ben-generate">{t("benefitDialog.ajouterLEntreeChaqueMois")}</Label>
          </div>
          <div className="grid gap-2">
            <Label>{t("benefitDialog.logo")}</Label>
            <LogoPicker value={form.logo} suggestFor={form.organization || form.name} onChange={(logo) => set({ logo })} />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field id="ben-start" label={t("benefitDialog.percueDepuis")} type="date" value={form.start_date} onChange={(v) => set({ start_date: v })} />
            <Field id="ben-note" label={t("benefitDialog.note")} placeholder={t("benefitDialog.facultatif")} value={form.note} onChange={(v) => set({ note: v })} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("benefitDialog.annuler")}</Button>
          <Button onClick={save} disabled={saving} className="bg-slate-900 text-white">{t("benefitDialog.enregistrer")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface FieldProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: string
  inputMode?: "decimal" | "numeric"
}

function Field({ id, label, value, onChange, placeholder, type, inputMode }: FieldProps) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type={type} inputMode={inputMode} placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}
