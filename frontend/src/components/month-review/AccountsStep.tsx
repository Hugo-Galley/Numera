import { useState } from "react"
import { CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

export function AccountsStep({
  step,
  onChanged,
}: {
  step: MonthReview["accounts"]
  onChanged: () => void
}) {
  const [busyId, setBusyId] = useState<number | null>(null)

  async function verify(id: number) {
    setBusyId(id)
    try {
      await api.post(`/accounts/${id}/verify`)
      toast.success("Solde validé")
      onChanged()
    } catch {
      toast.error("Échec de la validation")
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <p className="text-sm text-slate-600">
          Comparez le solde affiché avec celui de votre relevé, puis validez chaque compte.
        </p>
        <ul className="divide-y">
          {step.accounts.map((acc) => (
            <li key={acc.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <p className="font-medium">{acc.name}</p>
                <p className="text-xs text-slate-500">
                  Dernière validation : {new Date(acc.last_verified_at).toLocaleDateString("fr-FR")}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="amount-blur font-semibold">{formatCurrency(acc.balance, acc.currency)}</span>
                {acc.verified_since_month_end ? (
                  <span className="flex items-center gap-1 text-sm text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" /> Validé
                  </span>
                ) : (
                  <Button size="sm" variant="outline" disabled={busyId === acc.id} onClick={() => verify(acc.id)}>
                    Valider le solde
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
