import { Activity, ArrowDownRight, ArrowUpRight, Percent, Plus, Shield, Tag, Target, TrendingDown, TrendingUp } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatRate } from "@/lib/utils"
import { fr } from "date-fns/locale"
import { Account } from "./types"
import type { AccountDetailView } from "./useAccountDetail"

/** Indicateurs du compte et totaux par tag. */
export function AccountKpis({ ctx }: { ctx: AccountDetailView }) {
  const { account, currentBalance, formatCurrency, id, investmentData, isInvestment, stats, tagTotals } = ctx
  return (
    <>
      {/* Account KPIs : 2 colonnes compactes sur mobile pour que la liste ne soit pas repoussée de deux écrans */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6 max-sm:[&_.text-2xl]:text-lg max-sm:[&_p.text-xs]:hidden">
        <Card className="theme-island col-span-2 lg:col-span-1 border-none shadow-md bg-slate-900 text-white">
          <CardHeader className="pb-2">
            <CardDescription className="text-slate-400 font-medium">Solde Actuel</CardDescription>
            <CardTitle className="text-3xl font-bold">{formatCurrency(currentBalance || 0)}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-2">
              <TrendingUp className="h-3 w-3" />
              {/* Date de la dernière validation explicite du solde (et non « aujourd'hui » codé en dur) */}
              <span>
                {account.last_verified_at
                  ? `Solde vérifié le ${new Date(account.last_verified_at).toLocaleDateString("fr-FR")}`
                  : "Solde jamais vérifié"}
              </span>
            </div>
          </CardContent>
        </Card>

        {account.type === "assurance_vie" ? (
          <>
            <Card className="shadow-sm border border-slate-100 hover:border-slate-200 transition-all">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium text-slate-500">Fonds Euro ({account.fonds_euros_pct || 0}%)</CardDescription>
                <Shield className="h-4 w-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
                  {formatCurrency((currentBalance || 0) * ((account.fonds_euros_pct || 0) / 100))}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Capital garanti</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border border-slate-100 hover:border-slate-200 transition-all">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium text-slate-500">Unités de Compte ({account.fonds_investis_pct || 0}%)</CardDescription>
                <TrendingUp className="h-4 w-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
                  {formatCurrency((currentBalance || 0) * ((account.fonds_investis_pct || 0) / 100))}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Fonds investis (UC)</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border border-slate-100 hover:border-slate-200 transition-all">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium text-slate-500">Plus-value Latente</CardDescription>
                <Activity className={`h-4 w-4 ${((investmentData?.totals?.gain_eur || 0) >= 0) ? "text-emerald-500" : "text-rose-500"}`} />
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${((investmentData?.totals?.gain_eur || 0) >= 0) ? "text-emerald-600" : "text-rose-600"} amount-blur`}>
                  {((investmentData?.totals?.gain_eur || 0) >= 0) ? "+" : ""}{formatCurrency(investmentData?.totals?.gain_eur || 0)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Evolution du capital</p>
              </CardContent>
            </Card>
          </>
        ) : isInvestment ? (
          <>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Net Investi</CardDescription>
                <Target className="h-4 w-4 text-slate-400" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900">
                  {formatCurrency(investmentData?.totals?.net_invested || 0)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Versements - Retraits</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Gain total</CardDescription>
                <Activity className="h-4 w-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${(investmentData?.totals?.gain_eur || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {formatCurrency(investmentData?.totals?.gain_eur || 0)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Valeur − net investi (détail plus bas)</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Performance</CardDescription>
                <Percent className="h-4 w-4 text-slate-400" />
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${(investmentData?.totals?.performance_pct || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {formatRate(investmentData?.totals?.performance_pct)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Rendement global</p>
              </CardContent>
            </Card>
          </>
        ) : (
          <>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Flux Net du Mois</CardDescription>
                {(stats?.monthlyNetFlow || 0) >= 0 
                  ? <TrendingUp className="h-4 w-4 text-emerald-500" />
                  : <TrendingDown className="h-4 w-4 text-rose-500" />}
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${(stats?.monthlyNetFlow || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {(stats?.monthlyNetFlow || 0) >= 0 ? "+" : ""}{formatCurrency(stats?.monthlyNetFlow || 0)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Entrées − Sorties ce mois</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Variation Mensuelle</CardDescription>
                {stats?.monthlyVariation !== null && stats?.monthlyVariation !== undefined
                  ? (stats.monthlyVariation >= 0 
                      ? <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                      : <ArrowDownRight className="h-4 w-4 text-rose-500" />)
                  : <Activity className="h-4 w-4 text-slate-400" />}
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${stats?.monthlyVariation === null || stats?.monthlyVariation === undefined ? "text-slate-500" : stats.monthlyVariation >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {stats?.monthlyVariation !== null && stats?.monthlyVariation !== undefined
                    ? formatRate(stats.monthlyVariation, 1, true)
                    : "—"}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">vs mois précédent</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Panier Moyen</CardDescription>
                <Activity className="h-4 w-4 text-slate-400" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold">{formatCurrency(stats?.avgTx || 0)}</CardTitle>
                <p className="text-xs text-slate-400 mt-2">Par dépense effectuée</p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {tagTotals.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="col-span-full shadow-sm border-slate-100">
            <CardHeader className="pb-3 border-b border-slate-50 bg-slate-50/30">
              <div className="flex items-center gap-2">
                <Tag className="h-4 w-4 text-slate-400" />
                <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-500">Dépenses par tag</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="flex flex-wrap gap-4">
                {tagTotals.map((t) => (
                  <div key={t.id} className="flex items-center gap-3 p-3 bg-white border border-slate-100 rounded-2xl shadow-sm min-w-[150px]">
                    <div className="h-8 w-8 rounded-full flex items-center justify-center" style={{ backgroundColor: t.color || "#64748b" }}>
                      <Tag className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 leading-none mb-1">{t.name}</p>
                      <p className="text-lg font-black text-slate-900 leading-none">{formatCurrency(t.total_eur)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  )
}
