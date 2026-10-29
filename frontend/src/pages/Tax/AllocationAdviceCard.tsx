import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Compass } from "lucide-react"
import { Link } from "react-router-dom"
import { KIND_LABELS } from "./types"
import { Money } from "./TaxWidgets"
import type { TaxCtx } from "./useTax"

/** Conseils d'allocation entre enveloppes. */
export function AllocationAdviceCard({ ctx }: { ctx: TaxCtx }) {
  const { advice, overview } = ctx
  return (
    <>
      {advice.length > 0 && (
        <Card className="border-emerald-200 bg-emerald-50/40">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Compass className="h-4 w-4 text-emerald-600" /> Où placer ton prochain euro
            </CardTitle>
            <CardDescription>
              Ordre de remplissage conseillé selon tes plafonds restants
              {overview?.precaution_months != null && <> et ton épargne de précaution ({overview.precaution_months.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} mois de dépenses)</>}.
              Règle générale, pas un conseil personnalisé.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {advice.map((step) => (
                <li key={step.rank} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-sm font-bold text-white">{step.rank}</span>
                  <div className="min-w-0 text-sm">
                    <p className="font-semibold text-slate-900">
                      {step.account_id ? (
                        <Link to={`/accounts/${step.account_id}`} className="hover:underline">{step.account_name}</Link>
                      ) : (step.account_name ?? KIND_LABELS[step.kind])}
                      {step.remaining != null && step.remaining > 0 && (
                        <span className="ml-2 font-normal text-muted-foreground">· encore <Money value={step.remaining} /> de place</span>
                      )}
                    </p>
                    <p className="text-slate-600">{step.reason}</p>
                  </div>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}
    </>
  )
}
