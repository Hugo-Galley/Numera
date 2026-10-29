import { Activity, Plus } from "lucide-react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { format } from "date-fns"
import { fr } from "date-fns/locale"
import type { AccountDetailView } from "./useAccountDetail"

/** Graphiques d'évolution du compte (et de performance pour un compte d'investissement). */
export function AccountCharts({ ctx }: { ctx: AccountDetailView }) {
  const { formatCurrency, id, investmentData, isInvestment, perfHistory, timeseries } = ctx
  return (
    <>
      {/* Charts Section */}
      <div className="w-full space-y-8">
        <Card className="shadow-sm overflow-hidden border-slate-100 w-full">
          <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg font-bold">{isInvestment ? "Évolution du capital" : "Évolution du solde"}</CardTitle>
              <CardDescription>Historique complet en temps réel.</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-white">Vue d'ensemble</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0 h-[300px] md:h-[450px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              {isInvestment ? (
                <AreaChart data={investmentData?.totals?.value_source === "positions" ? perfHistory : (investmentData?.value_series || [])} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorInv" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0f172a" stopOpacity={0.1}/><stop offset="95%" stopColor="#0f172a" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(val) => format(new Date(val), "dd/MM")} minTickGap={40} />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip labelFormatter={(val) => format(new Date(val), "PPP", { locale: fr })} formatter={(val: number, name: string) => [formatCurrency(val), name === "net_invested" ? "Investi" : "Valeur"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Area type="monotone" dataKey="current_value" stroke="#0f172a" fillOpacity={1} fill="url(#colorInv)" strokeWidth={4} />
                  {investmentData?.totals?.value_source === "positions" && (
                    <Area type="stepAfter" dataKey="net_invested" stroke="#94a3b8" strokeDasharray="5 4" fill="none" strokeWidth={2} />
                  )}
                </AreaChart>
              ) : (
                <AreaChart data={timeseries?.balance_points || []} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0f172a" stopOpacity={0.1}/><stop offset="95%" stopColor="#0f172a" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(val) => format(new Date(val), "dd/MM")} minTickGap={40} />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip labelFormatter={(val) => format(new Date(val), "PPP", { locale: fr })} formatter={(val: number) => [formatCurrency(val), "Solde"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Area type="monotone" dataKey="running_balance" stroke="#0f172a" fillOpacity={1} fill="url(#colorBalance)" strokeWidth={4} />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {isInvestment && (
          <Card className="shadow-sm overflow-hidden border-slate-100 w-full">
            <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg font-bold">Plus-value latente (€)</CardTitle>
                <CardDescription>Évolution des gains ou pertes cumulés.</CardDescription>
              </div>
              <Activity className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent className="p-0 h-[250px] md:h-[350px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={perfHistory} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPerf" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(val) => format(new Date(val), "dd/MM")} minTickGap={40} />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip labelFormatter={(val) => format(new Date(val), "PPP", { locale: fr })} formatter={(val: number) => [formatCurrency(val), "Performance"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Area type="monotone" dataKey="gain_eur" stroke="#10b981" fillOpacity={1} fill="url(#colorPerf)" strokeWidth={4} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  )
}
