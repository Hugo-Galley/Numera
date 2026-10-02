import { useState } from "react"
import { PortfolioHolding } from "@/types/diversity"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { SlidersHorizontal, Trash2, Globe, Layers } from "lucide-react"
import { PointZeroModal } from "./PointZeroModal"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { CompanyLogo } from "@/components/ui/CompanyLogo"

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
  const [decomposingId, setDecomposingId] = useState<number | null>(null)

  const handleDecompose = async (h: PortfolioHolding) => {
    setDecomposingId(h.id)
    const toastId = toast.loading(`Décomposition de ${h.ticker} en ligne...`)
    try {
      const res = await api.post<any>("/etf-profiles/auto-decompose", {
        symbol: h.ticker,
        name: h.asset_name,
        isin: h.isin,
      })
      if (res && res.id) {
        await api.put(`/holdings/${h.id}`, {
          etf_profile_id: res.id,
          is_etf: true,
        })
        toast.success(`${res.name} décomposé avec succès !`, { id: toastId })
        onRefresh()
      } else {
        toast.error("Impossible de décomposer ce fonds en ligne", { id: toastId })
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur de décomposition", { id: toastId })
    } finally {
      setDecomposingId(null)
    }
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(val)
  }

  const totalValue = holdings.reduce((acc, h) => acc + (h.current_value_eur || 0), 0)

  const handleDelete = async (holdingId: number, name: string) => {
    if (!confirm(`Supprimer la position sur ${name} ?`)) return
    try {
      await api.delete(`/holdings/${holdingId}`)
      toast.success("Position supprimée")
      onRefresh()
    } catch (err) {
      toast.error("Erreur lors de la suppression")
    }
  }

  return (
    <>
      <Card className="shadow-sm">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-slate-500" />
              <CardTitle className="text-lg font-bold">Positions Actuelles (Actions & ETFs)</CardTitle>
            </div>
            <CardDescription className="text-sm mt-1">
              Valorisation en direct de vos lignes boursières au cours de marché.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={() => setPointZeroOpen(true)}
              className="gap-2"
            >
              <SlidersHorizontal className="h-4 w-4" />
              Point Zéro / État des Lieux
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {holdings.length === 0 ? (
            <div className="p-10 text-center space-y-3">
              <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Layers className="h-6 w-6" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h4 className="font-semibold text-base text-slate-900">Aucune position active renseignée</h4>
                <p className="text-sm text-slate-500">
                  Définissez votre <strong>Point Zéro</strong> en indiquant le nombre de parts détenues. Numera valorise vos positions au cours réel du marché.
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setPointZeroOpen(true)}
                className="gap-2 mt-2"
              >
                <SlidersHorizontal className="h-4 w-4" />
                Définir l'état des lieux
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="font-semibold text-slate-600">Actif / Symbole</TableHead>
                    <TableHead className="font-semibold text-slate-600">Type</TableHead>
                    <TableHead className="text-right font-semibold text-slate-600">Parts</TableHead>
                    <TableHead className="text-right font-semibold text-slate-600">Cours actuel</TableHead>
                    <TableHead className="text-right font-semibold text-slate-600">Valeur totale</TableHead>
                    <TableHead className="text-right font-semibold text-slate-600">Plus-value latente</TableHead>
                    <TableHead className="text-right font-semibold text-slate-600">Poids</TableHead>
                    <TableHead className="text-right w-[90px] font-semibold text-slate-600">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {holdings.map((h) => {
                    const weightPct = totalValue > 0 ? ((h.current_value_eur || 0) / totalValue) * 100 : 0

                    return (
                      <TableRow key={h.id} className="hover:bg-slate-50 transition-colors">
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <CompanyLogo
                              ticker={h.ticker}
                              name={h.asset_name}
                              isin={h.isin}
                              className="h-8 w-8 rounded-lg"
                            />
                            <div className="flex flex-col min-w-0">
                              <span className="font-bold text-slate-900 text-sm truncate max-w-[260px]" title={h.asset_name || h.ticker}>
                                {h.asset_name || h.ticker}
                              </span>
                              <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono mt-0.5">
                                <span className="font-medium text-slate-400">{h.ticker}</span>
                                {h.isin && (
                                  <>
                                    <span className="text-slate-300">•</span>
                                    <span className="text-slate-400 text-[11px]">{h.isin}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </TableCell>

                        <TableCell>
                          {h.is_etf || h.etf_profile_id ? (
                            <Badge variant="secondary" className="font-normal text-xs">
                              {h.etf_profile_id ? "ETF (décomposé)" : "ETF"}
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="font-normal text-xs text-slate-600">
                              Action
                            </Badge>
                          )}
                        </TableCell>

                        <TableCell className="text-right font-mono text-sm font-medium">
                          {h.quantity}
                        </TableCell>

                        <TableCell className="text-right font-mono text-sm">
                          {h.current_price ? (
                            <div className="flex flex-col items-end">
                              <span className="text-slate-900 font-medium">
                                {formatCurrency(h.current_price_eur || h.current_price)}
                              </span>
                              {h.currency && h.currency !== "EUR" && (
                                <span className="text-[10px] text-slate-400 font-normal">
                                  ({h.current_price.toFixed(2)} {h.currency})
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 italic text-xs">-</span>
                          )}
                        </TableCell>

                        <TableCell className="text-right font-mono font-bold text-sm text-slate-900">
                          <span className="amount-blur">{formatCurrency(h.current_value_eur || 0)}</span>
                        </TableCell>

                        <TableCell className="text-right font-mono text-sm font-semibold">
                          {h.gain_eur !== undefined && h.gain_eur !== null ? (
                            <div className="flex flex-col items-end">
                              <span className={`amount-blur ${h.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                {h.gain_eur >= 0 ? "+" : ""}{formatCurrency(h.gain_eur)}
                              </span>
                              <span className={`text-[11px] font-medium ${h.gain_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                ({h.gain_eur >= 0 ? "+" : ""}{h.gain_pct}%)
                              </span>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic text-xs">-</span>
                          )}
                        </TableCell>

                        <TableCell className="text-right font-mono text-xs text-slate-500 font-medium">
                          {weightPct.toFixed(1)}%
                        </TableCell>

                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {!h.etf_profile_id && (h.is_etf || h.ticker.startsWith("0P")) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-slate-500 hover:text-slate-900"
                                onClick={() => handleDecompose(h)}
                                disabled={decomposingId === h.id}
                                title="Décomposer en ligne"
                              >
                                <Globe className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-slate-400 hover:text-rose-600"
                              onClick={() => handleDelete(h.id, h.asset_name)}
                              title="Supprimer la position"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
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
