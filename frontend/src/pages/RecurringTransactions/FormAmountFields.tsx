import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Formulaire : montant, catégorie, virement et fréquence. */
export function FormAmountFields({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { accounts, categories, formData, selectedAccount, setFormData, transferToInvestment } = ctx
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="account">Compte</Label>
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
          <Label htmlFor="category">Catégorie</Label>
          <Select
            value={formData.category_id}
            onValueChange={(v) => setFormData({ ...formData, category_id: v })}
          >
            <SelectTrigger id="category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Sans catégorie</SelectItem>
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
          <Label htmlFor="transfer-to">Virement vers un compte (optionnel)</Label>
          <Select
            value={formData.transfer_to_account_id}
            onValueChange={(v) => setFormData({ ...formData, transfer_to_account_id: v })}
          >
            <SelectTrigger id="transfer-to">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Non, c'est une dépense</SelectItem>
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
                ? "Chaque échéance crée la sortie, le dépôt et l'achat des parts (au cours de clôture de la date), déjà liés : renseignez le titre ci-dessous."
                : "Chaque échéance crée la sortie et l'entrée correspondante, déjà liées : le montant n'est pas compté deux fois."}
            </p>
          )}
          {formData.transfer_to_account_id !== "none" && (
            <div className="grid gap-2 pt-1">
              <Label htmlFor="transfer_credit_day">Arrivée sur le compte destination (jour du mois)</Label>
              <Input
                id="transfer_credit_day"
                type="number" inputMode="decimal"
                min="1"
                max="31"
                placeholder="Le jour même"
                value={formData.transfer_credit_day}
                onChange={(e) => setFormData({ ...formData, transfer_credit_day: e.target.value })}
              />
              <p className="text-xs text-slate-500">
                {formData.transfer_credit_day
                  ? `Débité le ${formData.day_of_month || "…"}, crédité le ${formData.transfer_credit_day} suivant : d'ici là l'argent est en transit, rien n'est crédité.`
                  : "Vide : crédité le jour du débit. Renseignez un jour si le virement met du temps à arriver."}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="frequency">Fréquence</Label>
          <Select
            value={formData.frequency}
            onValueChange={(v) => setFormData({ ...formData, frequency: v })}
          >
            <SelectTrigger id="frequency">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="weekly">Hebdomadaire</SelectItem>
              <SelectItem value="monthly">Mensuelle</SelectItem>
              <SelectItem value="quarterly">Trimestrielle</SelectItem>
              <SelectItem value="yearly">Annuelle</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="day_of_month">Jour du mois</Label>
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
