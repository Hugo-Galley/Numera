import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Formulaire : nom, logo, compte et type. */
export function FormMainFields({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { formData, isInvestment, setFormData } = ctx
  return (
    <>
      <div className="grid gap-2">
        <Label htmlFor="name">Nom / Marchand</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Ex: Loyer, Netflix, Salaire..."
        />
      </div>

      <div className="grid gap-2">
        <Label>Logo</Label>
        <LogoPicker
          value={formData.logo}
          suggestFor={formData.name}
          onChange={(logo) => setFormData((prev) => ({ ...prev, logo }))}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label htmlFor="type">Type</Label>
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
                  <SelectItem value="Sortie">Sortie</SelectItem>
                  <SelectItem value="Entree">Entrée</SelectItem>
                  <SelectItem value="Interets">Intérêts</SelectItem>
                </>
              ) : (
                <>
                  <SelectItem value="versement">Versement</SelectItem>
                  <SelectItem value="retrait">Retrait</SelectItem>
                  <SelectItem value="dividende">Dividende</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="amount">Montant</Label>
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
