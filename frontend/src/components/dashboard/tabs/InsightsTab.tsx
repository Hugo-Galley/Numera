import { HeartPulse, Sparkles, AlertTriangle } from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatCurrency } from "@/lib/utils"

interface InsightsTabProps {
  insights: any
}

export function InsightsTab({ insights }: InsightsTabProps) {
  return (
    <div className="grid gap-8 lg:grid-cols-12">
      <Card className="lg:col-span-4 shadow-sm border-slate-100 overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 text-white">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <HeartPulse className="h-5 w-5 text-emerald-400" />
            Santé Financière
          </CardTitle>
          <CardDescription className="text-slate-400">Score global de votre situation.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-10">
          <div className="relative flex items-center justify-center">
            <svg className="w-48 h-48 transform -rotate-90">
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="currentColor"
                strokeWidth="12"
                fill="transparent"
                className="text-slate-700"
              />
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="currentColor"
                strokeWidth="12"
                fill="transparent"
                strokeDasharray={552.92}
                strokeDashoffset={552.92 - (552.92 * (insights?.health_score?.total_score || 0)) / 100}
                strokeLinecap="round"
                className={`${
                  (insights?.health_score?.total_score || 0) > 70 ? "text-emerald-400" : (insights?.health_score?.total_score || 0) > 40 ? "text-amber-400" : "text-rose-400"
                } transition-all duration-1000 ease-out`}
              />
            </svg>
            <div className="absolute text-center">
              <span className="text-5xl font-black">{Math.round(insights?.health_score?.total_score || 0)}</span>
              <span className="text-slate-400 block text-sm font-bold mt-1">/ 100</span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 w-full mt-10">
            {insights?.health_score?.metrics.map((m: any, i: number) => (
              <div key={i} className="bg-slate-800/50 p-3 rounded-2xl border border-slate-700/50">
                <p className="text-[10px] uppercase font-black text-slate-500 tracking-wider mb-1">{m.name}</p>
                <p className="text-sm font-bold flex items-center justify-between">
                  {m.value}{m.unit}
                  <span className={`h-1.5 w-1.5 rounded-full ${m.status === 'good' ? 'bg-emerald-400' : m.status === 'warning' ? 'bg-amber-400' : 'bg-rose-400'}`} />
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="lg:col-span-8 space-y-6">
        <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-amber-500" />
          Analyse & Conseils
        </h3>
        <div className="grid gap-4">
          {insights?.insights.map((insight: any, i: number) => (
            <Card key={i} className={`shadow-sm border-l-4 ${
              insight.type === 'anomaly' ? 'border-l-amber-500' : 'border-l-emerald-500'
            } hover:bg-slate-50 transition-colors`}>
              <CardHeader className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex gap-4">
                    <div className={`mt-1 p-2 rounded-xl ${
                      insight.type === 'anomaly' ? 'bg-amber-100 text-amber-600' : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {insight.type === 'anomaly' ? <AlertTriangle className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
                    </div>
                    <div>
                      <CardTitle className="text-lg font-bold text-slate-900">{insight.title}</CardTitle>
                      <CardDescription className="text-slate-600 mt-1">{insight.description}</CardDescription>
                    </div>
                  </div>
                  {insight.value && (
                    <Badge variant="outline" className={insight.type === 'anomaly' ? 'text-amber-700 bg-amber-50' : 'text-emerald-700 bg-emerald-50'}>
                      {insight.type === 'anomaly' ? `+${formatCurrency(insight.value)}` : insight.unit === '%' ? `${insight.value}%` : formatCurrency(insight.value)}
                    </Badge>
                  )}
                </div>
              </CardHeader>
            </Card>
          ))}
          {(!insights?.insights || insights?.insights.length === 0) && (
            <div className="py-20 text-center bg-slate-50 rounded-3xl border border-dashed">
              <p className="text-slate-400 font-medium">Tout semble sous contrôle ! Aucun insight particulier ce mois-ci.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
