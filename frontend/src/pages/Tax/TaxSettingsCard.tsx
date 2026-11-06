import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TMI_OPTIONS, TaxSettings } from "./types"
import type { TaxCtx } from "./useTax"

/** Réglages fiscaux (TMI, situation). */
export function TaxSettingsCard({ ctx }: { ctx: TaxCtx }) {
  const { t } = useTranslation("tax")
  const { draft, saveSettings, setDraft, settingsOpen } = ctx
  return (
    <>
      {settingsOpen && draft && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("taxSettingsCard.reglagesFiscaux")}</CardTitle>
            <CardDescription>{t("taxSettingsCard.serventAuCalculDuPlafond")}</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="grid gap-2">
              <Label htmlFor="tax-tmi">{t("taxSettingsCard.trancheMarginaleTmi")}</Label>
              <Select value={String(draft.tmi_pct)} onValueChange={(v) => setDraft({ ...draft, tmi_pct: Number(v) })}>
                <SelectTrigger id="tax-tmi"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TMI_OPTIONS.map((t) => <SelectItem key={t} value={String(t)}>{t} %</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tax-income">{t("taxSettingsCard.revenusProfessionnelsDeLAnnee")}</Label>
              <Input
                id="tax-income"
                type="number" inputMode="decimal"
                min={0}
                value={draft.prior_year_pro_income}
                onChange={(e) => setDraft({ ...draft, prior_year_pro_income: Number(e.target.value) || 0 })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tax-household">{t("taxSettingsCard.foyer")}</Label>
              <Select value={draft.household} onValueChange={(v) => setDraft({ ...draft, household: v as TaxSettings["household"] })}>
                <SelectTrigger id="tax-household"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">{t("taxSettingsCard.seul")}</SelectItem>
                  <SelectItem value="couple">{t("taxSettingsCard.couple")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tax-gross">{t("taxSettingsCard.salaireBrutAnnuelPourLe")}</Label>
              <Input
                id="tax-gross"
                type="number" inputMode="decimal"
                min={0}
                value={draft.gross_annual_salary}
                onChange={(e) => setDraft({ ...draft, gross_annual_salary: Number(e.target.value) || 0 })}
              />
            </div>
            <div className="md:col-span-3">
              <Button className="h-11 w-full sm:h-10 sm:w-auto" onClick={saveSettings}>{t("taxSettingsCard.enregistrer")}</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </>
  )
}
