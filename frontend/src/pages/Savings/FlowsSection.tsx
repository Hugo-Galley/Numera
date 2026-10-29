import { Activity, TrendingUp, Zap } from "lucide-react"
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { SavingsCtx } from "./useSavings"

/** Section 2 : dynamique et flux. */
export function FlowsSection({ ctx }: { ctx: SavingsCtx }) {
  const { analytics, history, isMobile, period, shareLabel } = ctx
  return (
    <>
      {/* SECTION 2 : DYNAMIQUE ET FLUX */}
      <section className="space-y-4 md:space-y-6">
        <div className="flex items-center gap-2 border-b pb-2">
          <Activity className="h-5 w-5 text-slate-400" />
          <h2 className="text-xl font-bold text-slate-900">Dynamique & Flux</h2>
        </div>

        <div className="grid gap-4 md:gap-6 grid-cols-1 md:grid-cols-2">
          <Card className="shadow-sm border-slate-100 hover:shadow-md transition-shadow">
            <CardContent className="p-4 md:p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 bg-blue-50 rounded-xl flex items-center justify-center">
                    <Zap className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-500">Flux d'Épargne {period === "all-time" ? "Total" : "Mensuel"}</p>
                    <p className="whitespace-nowrap text-2xl font-bold tabular-nums text-slate-900">
                      {formatCurrency(analytics?.epargne_realisee || 0)}
                    </p>
                  </div>
                </div>
              </div>
              <div className="pt-4 border-t border-slate-100">
                <div className="h-10 w-full mb-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart layout="vertical" data={[{
                      name: 'Flux',
                      Cash: analytics?.reste_tresorerie || 0,
                      Investissements: analytics?.investissements_du_mois || 0
                    }]} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                      <XAxis type="number" hide />
                      <YAxis dataKey="name" type="category" hide />
                      <Tooltip cursor={{fill: 'transparent'}} formatter={(v: number, _n: string, item: any) => shareLabel(v, item?.payload, ['Cash', 'Investissements'])} contentStyle={{ fontSize: '12px', borderRadius: '8px', border: 'none', boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                      <ReferenceLine x={0} stroke="#e2e8f0" />
                      <Bar dataKey="Cash" stackId="a" fill={(analytics?.reste_tresorerie || 0) >= 0 ? "#94a3b8" : "#f43f5e"} radius={[4, 4, 4, 4]} barSize={12} />
                      <Bar dataKey="Investissements" stackId="a" fill="#0f172a" radius={[4, 4, 4, 4]} barSize={12} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-between items-center">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <div className={`w-2 h-2 rounded-full ${(analytics?.reste_tresorerie || 0) >= 0 ? 'bg-slate-400' : 'bg-rose-500'}`} />
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Reste en trésorerie</p>
                    </div>
                    <p className="font-semibold text-slate-700 text-sm mt-0.5">{formatCurrency(analytics?.reste_tresorerie || 0)}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <div className="w-2 h-2 rounded-full bg-slate-900" />
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Investissements</p>
                    </div>
                    <p className="font-semibold text-slate-700 text-sm mt-0.5">{formatCurrency(analytics?.investissements_du_mois || 0)}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-100 hover:shadow-md transition-shadow">
            <CardContent className="p-4 md:p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 bg-amber-50 rounded-xl flex items-center justify-center">
                    <TrendingUp className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-500">Intérêts Perçus {period === "all-time" ? "Cumulés" : "du Mois"}</p>
                    <p className="whitespace-nowrap text-2xl font-bold tabular-nums text-slate-900">
                      {formatCurrency(analytics?.interets_totaux || 0)}
                    </p>
                  </div>
                </div>
              </div>
              <div className="pt-4 border-t border-slate-100">
                 <p className="text-sm text-slate-500">
                   L'argent qui travaille pour vous. Ces gains passifs augmentent votre capital sans effort supplémentaire.
                 </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
          <Card className="shadow-sm border-slate-100">
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Historique des Flux d'Épargne</CardTitle>
              <CardDescription>Répartition de votre épargne mensuelle sur l'année.</CardDescription>
            </CardHeader>
            <CardContent className="h-[260px] px-2 md:h-[300px] md:px-6">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={history} margin={{ top: 10, right: 10, left: isMobile ? -8 : -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} dy={10} interval="preserveStartEnd" minTickGap={12} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}€`} />
                  <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(v: number, _n: string, item: any) => shareLabel(v, item?.payload, ['cash_flow', 'investissements', 'interets'])} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px', paddingBottom: '20px' }}/>
                  <Bar dataKey="cash_flow" name="Cash Restant" stackId="a" fill="#94a3b8" radius={[0, 0, 0, 0]} maxBarSize={40} />
                  <Bar dataKey="investissements" name="Investissements" stackId="a" fill="#0f172a" radius={[0, 0, 0, 0]} maxBarSize={40} />
                  <Bar dataKey="interets" name="Intérêts" stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-slate-100">
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Évolution du Taux d'Épargne (%)</CardTitle>
              <CardDescription>Visualisez la régularité de vos efforts.</CardDescription>
            </CardHeader>
            <CardContent className="h-[260px] px-2 md:h-[300px] md:px-6">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart 
                  data={history.map(h => ({ label: h.label, rate: h.taux_epargne }))}
                  margin={{ top: 10, right: 10, left: isMobile ? -8 : -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorRate" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} dy={10} interval="preserveStartEnd" minTickGap={12} />
                  <YAxis domain={[-100, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}%`} />
                  <Tooltip formatter={(v: number) => [formatRate(v, 1), "Taux"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Area type="monotone" dataKey="rate" stroke="#3b82f6" fillOpacity={1} fill="url(#colorRate)" strokeWidth={3} dot={{ r: 4, fill: "#3b82f6", strokeWidth: 2, stroke: "#fff" }} activeDot={{ r: 6 }} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  )
}
