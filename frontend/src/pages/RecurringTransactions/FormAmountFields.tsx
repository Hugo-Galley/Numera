import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Formulaire : montant, catégorie, virement et fréquence. */
export function FormAmountFields({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { t } = useTranslation("recurring")
  const { accounts, categories, formData, selectedAccount, setFormData, transferToInvestment } = ctx
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="account">{t("formAmountFields.compte")}</Label>
          <Select
            value={formData.account_id}
            onValueChange={(v) => setFormData({ ...formData, account_id: v })}
          >
            <SelectTrigger id="account">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {accounts.map((acc) => (
                <SelectItem key={acc.id} value={acc.id.toString()}>
                  {acc.name} ({acc.currency})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="category">{t("formAmountFields.categorie")}</Label>
          <Select
            value={formData.category_id}
            onValueChange={(v) => setFormData({ ...formData, category_id: v })}
          >
            <SelectTrigger id="category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t("formAmountFields.sansCategorie")}</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.id} value={cat.id.toString()}>
                  {cat.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {formData.type === "Sortie" && selectedAccount?.type !== "investissement" && (
        <div className="grid gap-2">
          <Label htmlFor="transfer-to">{t("formAmountFields.virementVersUnCompteOptionnel")}</Label>
          <Select
            value={formData.transfer_to_account_id}
            onValueChange={(v) => setFormData({ ...formData, transfer_to_account_id: v })}
          >
            <SelectTrigger id="transfer-to">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t("formAmountFields.nonCEstUneDepense")}</SelectItem>
              {accounts
                .filter((acc) => acc.id.toString() !== formData.account_id)
                .map((acc) => (
                  <SelectItem key={acc.id} value={acc.id.toString()}>
                    {acc.name} ({acc.currency})
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          {formData.transfer_to_account_id !== "none" && (
            <p className="text-xs text-slate-500">
              {transferToInvestment
                ? t("formAmountFields.chaqueEcheanceCreeLaSortie")
                : t("formAmountFields.chaqueEcheanceCreeLaSortie2")}
            </p>
          )}
          {formData.transfer_to_account_id !== "none" && (
            <div className="grid gap-2 pt-1">
              <Label htmlFor="transfer_credit_day">{t("formAmountFields.arriveeSurLeCompteDestination")}</Label>
              <Input
                id="transfer_credit_day"
                type="number" inputMode="decimal"
                min="1"
                max="31"
                placeholder={t("formAmountFields.leJourMeme")}
                value={formData.transfer_credit_day}
                onChange={(e) => setFormData({ ...formData, transfer_credit_day: e.target.value })}
              />
              <p className="text-xs text-slate-500">
                {formData.transfer_credit_day
                  ? i18n.t("misc.transitNote", { ns: "recurring", debit: formData.day_of_month || "…", credit: formData.transfer_credit_day })
                  : t("formAmountFields.videCrediteLeJourDu")}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="frequency">{t("formAmountFields.frequence")}</Label>
          <Select
            value={formData.frequency}
            onValueChange={(v) => setFormData({ ...formData, frequency: v })}
          >
            <SelectTrigger id="frequency">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="weekly">{t("formAmountFields.hebdomadaire")}</SelectItem>
              <SelectItem value="monthly">{t("formAmountFields.mensuelle")}</SelectItem>
              <SelectItem value="quarterly">{t("formAmountFields.trimestrielle")}</SelectItem>
              <SelectItem value="yearly">{t("formAmountFields.annuelle")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="day_of_month">{t("formAmountFields.jourDuMois")}</Label>
          <Input
            id="day_of_month"
            type="number" inputMode="decimal"
            min="1"
            max="31"
            value={formData.day_of_month}
            onChange={(e) => setFormData({ ...formData, day_of_month: e.target.value })}
          />
        </div>
      </div>
    </>
  )
}
