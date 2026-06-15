import { TrendingUp, ArrowUpRight, ArrowDownRight, Sparkles } from "lucide-react"
import { format } from "date-fns"
import { fr } from "date-fns/locale"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine
} from "recharts"

const safeFormat = (dateStr: string | null | undefined, formatStr: string) => {
  if (!dateStr) return "-"
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return "-"
    return format(d, formatStr, { locale: fr })
  } catch (e) {
    return "-"
  }
}

interface ProjectionsTabProps {
  projection: any
  displayCurrency: string
}

export function ProjectionsTab({ projection, displayCurrency }: ProjectionsTabProps) {
  return (
    <div className="space-y-8">
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="shadow-sm border-slate-100">
          <CardHeader className="pb-2">
            <CardDescription className="font-medium text-slate-500">Solde Projeté (60j)</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
              {formatCurrency(projection?.projected_balance || 0, displayCurrency)}
            </CardTitle>
            <div className="flex items-center gap-1.5 mt-1">
               <TrendingUp className={`h-3.5 w-3.5 ${((projection?.projected_balance || 0) >= (projection?.current_balance || 0)) ? 'text-emerald-500' : 'text-rose-500'}`} />
               <span className={`text-xs font-bold ${((projection?.projected_balance || 0) >= (projection?.current_balance || 0)) ? 'text-emerald-600' : 'text-rose-600'}`}>
                 {((projection?.projected_balance || 0) - (projection?.current_balance || 0) > 0 ? "+" : "")}
                 {formatCurrency((projection?.projected_balance || 0) - (projection?.current_balance || 0), displayCurrency)}
               </span>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-100">
          <CardHeader className="pb-2">
            <CardDescription className="font-medium text-slate-500">Point le plus bas</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
              {formatCurrency(projection?.low_point || 0, displayCurrency)}
            </CardTitle>
            <p className="text-xs text-slate-400 mt-1 uppercase font-bold tracking-tight">
              Prévu le {projection?.low_point_date ? format(new Date(projection.low_point_date), "d MMMM", { locale: fr }) : "-"}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-100">
          <CardHeader className="pb-2">
            <CardDescription className="font-medium text-slate-500">Flux récurrents attendus</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold text-slate-900">
              {projection?.events?.length || 0}
            </CardTitle>
            <p className="text-xs text-slate-400 mt-1 uppercase font-bold tracking-tight">Prochains 60 jours</p>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <CardTitle className="text-lg">Évolution du Solde Projeté</CardTitle>
          <CardDescription>Projection basée sur vos revenus et dépenses récurrentes sur les 2 prochains mois.</CardDescription>
        </CardHeader>
        <CardContent className="p-0 sm:p-6 h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={projection?.points || []} margin={{ top: 40, right: 30, left: 20, bottom: 20 }}>
              <defs>
                <linearGradient id="colorProj" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="date" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 10, fill: '#64748b' }} 
                tickFormatter={(v) => safeFormat(v, "d MMM")}
                minTickGap={30}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 12, fill: '#64748b' }} 
                tickFormatter={(v) => `${Math.round(v)}€`}
              />
              <Tooltip 
                contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} 
                labelFormatter={(v) => format(new Date(v), "EEEE d MMMM", { locale: fr })}
                formatter={(v: number) => [formatCurrency(v, displayCurrency), "Solde estimé"]}
              />
              <Area type="monotone" dataKey="balance" name="Solde" stroke="#3b82f6" fill="url(#colorProj)" strokeWidth={4} />
              <ReferenceLine y={0} stroke="#f43f5e" strokeDasharray="3 3" />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-8 lg:grid-cols-2">
         <Card className="shadow-sm border-slate-100">
           <CardHeader>
             <CardTitle className="text-lg">Prochains flux</CardTitle>
             <CardDescription>Événements prévus dans les 30 prochains jours.</CardDescription>
           </CardHeader>
           <CardContent className="p-0">
             <div className="divide-y">
               {projection?.events?.slice(0, 10).map((ev: any, i: number) => (
                 <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                   <div className="flex items-center gap-3">
                     <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${ev.is_income ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                       {ev.is_income ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                     </div>
                     <div>
                       <p className="text-sm font-bold text-slate-900">{ev.name}</p>
                       <p className="text-[10px] text-slate-500 font-medium uppercase">{format(new Date(ev.date), "d MMMM", { locale: fr })}</p>
                     </div>
                   </div>
                   <span className={`text-sm font-black amount-blur ${ev.is_income ? 'text-emerald-600' : 'text-slate-900'}`}>
                     {ev.is_income ? '+' : '-'}{formatCurrency(ev.amount, displayCurrency)}
                   </span>
                 </div>
               ))}
             </div>
           </CardContent>
         </Card>

         <div className="space-y-6">
            <Card className="shadow-sm border-blue-100 bg-blue-50/20">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-blue-500" />
                  Analyse de trésorerie
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-slate-600 leading-relaxed">
                  Votre solde devrait rester **positif** sur toute la période projetée. 
                  Le point bas est estimé à <span className="font-bold text-slate-900 amount-blur">{formatCurrency(projection?.low_point || 0, displayCurrency)}</span>.
                </p>
                <div className="p-4 bg-white rounded-xl border border-blue-100 shadow-sm">
                   <p className="text-xs font-bold text-blue-800 uppercase mb-2">Conseil</p>
                   <p className="text-sm text-slate-700">Vous avez un excédent de trésorerie prévu de <span className="font-bold">{formatCurrency((projection?.projected_balance || 0) - (projection?.current_balance || 0), displayCurrency)}</span>. Envisagez un versement complémentaire vers votre compte d'épargne.</p>
                </div>
              </CardContent>
            </Card>
         </div>
      </div>
    </div>
  )
}
