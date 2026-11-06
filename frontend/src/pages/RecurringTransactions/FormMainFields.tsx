import { useTranslation } from "react-i18next"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Formulaire : nom, logo, compte et type. */
export function FormMainFields({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { t } = useTranslation("recurring")
  const { formData, isInvestment, setFormData } = ctx
  return (
    <>
      <div className="grid gap-2">
        <Label htmlFor="name">{t("formMainFields.nomMarchand")}</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder={t("formMainFields.exLoyerNetflixSalaire")}
        />
      </div>

      <div className="grid gap-2">
        <Label>{t("formMainFields.logo")}</Label>
        <LogoPicker
          value={formData.logo}
          suggestFor={formData.name}
          onChange={(logo) => setFormData((prev) => ({ ...prev, logo }))}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="type">{t("formMainFields.type")}</Label>
          <Select
            value={formData.type}
            onValueChange={(v) => setFormData({ ...formData, type: v })}
          >
            <SelectTrigger id="type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {!isInvestment ? (
                <>
                  <SelectItem value="Sortie">{t("formMainFields.sortie")}</SelectItem>
                  <SelectItem value="Entree">{t("formMainFields.entree")}</SelectItem>
                  <SelectItem value="Interets">{t("formMainFields.interets")}</SelectItem>
                </>
              ) : (
                <>
                  <SelectItem value="versement">{t("formMainFields.versement")}</SelectItem>
                  <SelectItem value="retrait">{t("formMainFields.retrait")}</SelectItem>
                  <SelectItem value="dividende">{t("formMainFields.dividende")}</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="amount">{t("formMainFields.montant")}</Label>
          <Input
            id="amount"
            type="number" inputMode="decimal"
            step="0.01"
            value={formData.amount}
            onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
          />
        </div>
      </div>
    </>
  )
}
