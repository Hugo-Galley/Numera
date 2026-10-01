import { useState } from "react"
import { PortfolioHolding } from "@/types/diversity"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Sparkles, TrendingUp, TrendingDown, Layers, Plus, Trash2 } from "lucide-react"
import { PointZeroModal } from "./PointZeroModal"
import { api } from "@/lib/api"
import { toast } from "sonner"

interface HoldingsTableProps {
  accountId: number
  accountName: string
  holdings: PortfolioHolding[]
  onRefresh: () => void
}

export function HoldingsTable({
  accountId,
  accountName,
  holdings,
  onRefresh,
}: HoldingsTableProps) {
  const [pointZeroOpen, setPointZeroOpen] = useState(false)

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(val)
  }

  const totalValue = holdings.reduce((acc, h) => acc + (h.current_value_eur || 0), 0)

  const handleDelete = async (holdingId: number, name: string) => {
    if (!confirm(`Supprimer la ligne ${name} ?`)) return
    try {
      await api.delete(`/holdings/${holdingId}`)
      toast.success("Ligne supprimée")
      onRefresh()
    } catch (err) {
      toast.error("Erreur lors de la suppression")
    }
  }

  return (
    <>
      <Card className="shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-3 border-b">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-indigo-500" />
              <CardTitle className="text-base font-bold">Positions Actuelles (Nombre de parts)</CardTitle>
            </div>
            <CardDescription className="text-xs mt-0.5">
              Valorisation en direct de vos lignes boursières au cours de marché.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={() => setPointZeroOpen(true)}
              className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs h-8"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Point Zéro / État des Lieux
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {holdings.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <div className="h-10 w-10 rounded-full bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 flex items-center justify-center mx-auto">
                <Sparkles className="h-5 w-5" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h4 className="font-semibold text-sm">Aucune position active renseignée</h4>
                <p className="text-xs text-muted-foreground">
                  Faites votre <strong>Point Zéro</strong> en 2 minutes. Numera scannera vos anciennes transactions pour vous proposer vos actifs sans modifier l'historique !
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setPointZeroOpen(true)}
                className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Lancer l'état des lieux initial
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 dark:bg-slate-800/50 text-muted-foreground uppercase font-semibold border-b">
                  <tr>
                    <th className="py-2.5 px-4">Actif / Symbole</th>
                    <th className="py-2.5 px-3 text-right">Parts</th>
                    <th className="py-2.5 px-3 text-right">Cours Réel</th>
                    <th className="py-2.5 px-3 text-right">Valeur Actuelle</th>
                    <th className="py-2.5 px-3 text-right">Plus-value</th>
                    <th className="py-2.5 px-3 text-right">Poids</th>
                    <th className="py-2.5 px-3 text-center"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {holdings.map((h) => {
                    const weightPct = totalValue > 0 ? ((h.current_value_eur || 0) / totalValue) * 100 : 0

                    return (
                      <tr key={h.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="py-2.5 px-4">
                          <div className="flex flex-col">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-sm">{h.ticker}</span>
                              {h.is_etf ? (
                                <Badge variant="outline" className="text-[10px] px-1 py-0 border-indigo-200 text-indigo-700 bg-indigo-50">
                                  ETF
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-[10px] px-1 py-0">
                                  Action
                                </Badge>
                              )}
                            </div>
                            <span className="text-muted-foreground text-[11px] truncate max-w-[200px]">{h.asset_name}</span>
                          </div>
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono font-medium">
                          {h.quantity}
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono">
                          {h.current_price ? (
                            <div className="flex items-center justify-end gap-1">
                              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                              <span>{h.current_price.toFixed(2)} {h.currency}</span>
                            </div>
                          ) : (
                            <span className="text-muted-foreground italic">-</span>
                          )}
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900 dark:text-slate-100">
                          {formatCurrency(h.current_value_eur || 0)}
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono">
                          {h.gain_eur !== undefined && h.gain_eur !== null ? (
                            <div className={`flex items-center justify-end gap-0.5 ${h.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                              {h.gain_eur >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                              <span>{h.gain_eur >= 0 ? "+" : ""}{formatCurrency(h.gain_eur)}</span>
                              <span className="text-[10px]">({h.gain_pct}%)</span>
                            </div>
                          ) : (
                            <span className="text-muted-foreground italic">-</span>
                          )}
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono font-medium">
                          {weightPct.toFixed(1)}%
                        </td>

                        <td className="py-2.5 px-3 text-center">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-muted-foreground hover:text-rose-600"
                            onClick={() => handleDelete(h.id, h.asset_name)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <PointZeroModal
        open={pointZeroOpen}
        onOpenChange={setPointZeroOpen}
        accountId={accountId}
        accountName={accountName}
        onBaselineSaved={onRefresh}
      />
    </>
  )
}
