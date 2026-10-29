import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TMI_OPTIONS, TaxSettings } from "./types"
import type { TaxCtx } from "./useTax"

/** Réglages fiscaux (TMI, situation). */
export function TaxSettingsCard({ ctx }: { ctx: TaxCtx }) {
  const { draft, saveSettings, setDraft, settingsOpen } = ctx
  return (
    <>
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
    </>
  )
}
