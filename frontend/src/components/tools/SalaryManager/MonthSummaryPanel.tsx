import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, Download, Wallet } from "lucide-react"
import { format } from "date-fns"
import { formatCurrency } from "@/lib/utils"
import { fr } from "date-fns/locale"
import type { SalaryManagerCtx } from "./useSalaryManager"

/** Synthèse du mois : salaire calculé, tickets et génération. */
export function MonthSummaryPanel({ ctx }: { ctx: SalaryManagerCtx }) {
  const { config, currentDate, generating, handleGenerate, handleReset, isGenerated, monthLoadFailed, nbTickets, salaryDate, summary } = ctx
  return (
    <>
      <div className="lg:col-span-1">
        <Card className="h-full flex flex-col shadow-md">
          <CardHeader className="border-b pb-4">
            <CardTitle className="text-lg flex flex-wrap gap-x-3 justify-between items-center">
              <span className="flex items-center gap-2">
                <Wallet className="h-5 w-5 text-primary" />
                Résumé du mois
              </span>
              <span className="text-sm font-medium text-muted-foreground">
                {format(currentDate, "MMMM yyyy", { locale: fr })}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 flex-1 flex flex-col">
            <div className="space-y-6 flex-1">

              {/* Banque */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  Reçu en Banque
                </h3>
                <div className="bg-muted/50 border rounded-xl p-4 text-sm shadow-inner">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-muted-foreground">Salaire net après primes</span>
                    <span className="font-medium">{summary ? formatCurrency(summary.net_salary) : "—"}</span>
                  </div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="min-w-0 text-muted-foreground">Déduction TR ({nbTickets} × {formatCurrency(config.ticket_employee_share)})</span>
                    <span className="text-destructive font-medium whitespace-nowrap tabular-nums">- {summary ? formatCurrency(summary.ticket_deduction) : "—"}</span>
                  </div>
                  <div className="border-t pt-3 flex justify-between items-center">
                    <span className="font-bold">Total versé</span>
                    <span className="font-black text-xl text-emerald-600 whitespace-nowrap tabular-nums">{summary ? formatCurrency(summary.real_salary) : "—"}</span>
                  </div>
                </div>
              </div>

              {/* TR */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  Titres-Restaurant (indicatif)
                </h3>
                <div className="bg-muted/50 border rounded-xl p-4 text-sm shadow-inner">
                  <p className="text-xs text-muted-foreground mb-2 italic">
                    Ce montant n'est pas suivi comme transaction
                  </p>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Tickets crédités ({nbTickets} × {formatCurrency(config.ticket_value)})</span>
                    <span className="font-black text-xl text-amber-500 whitespace-nowrap tabular-nums">+ {summary ? formatCurrency(summary.ticket_credit) : "—"}</span>
                  </div>
                </div>
              </div>

            </div>

            <div className="mt-6 pt-5 md:mt-8 md:pt-6 border-t">
              {isGenerated ? (
                <div className="flex flex-col gap-3">
                  <div className="bg-emerald-100 border border-emerald-200 text-emerald-700 p-4 rounded-xl flex items-center justify-center gap-2 font-medium shadow-sm">
                    <CheckCircle2 className="h-5 w-5" />
                    Salaire du mois généré
                  </div>
                  <Button variant="outline" className="h-11 w-full md:h-9" onClick={handleReset}>
                    Réinitialiser ce mois
                  </Button>
                </div>
              ) : (
                <Button 
                  className="w-full h-12 text-base font-bold shadow-lg transition-transform hover:scale-[1.02]" 
                  onClick={handleGenerate}
                  disabled={generating || !salaryDate || monthLoadFailed}
                >
                  {generating ? "Génération..." : <><Download className="mr-2 h-5 w-5" /> Générer les transactions</>}
                </Button>
              )}
              {!salaryDate && !isGenerated && (
                <p className="text-xs text-center text-slate-400 mt-3 font-medium">
                  Veuillez définir une date de versement dans le calendrier
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
