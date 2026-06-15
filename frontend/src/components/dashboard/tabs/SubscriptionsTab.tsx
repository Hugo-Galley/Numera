import { Briefcase } from "lucide-react"
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
  PieChart,
  Pie,
  Cell,
  Tooltip
} from "recharts"

const COLORS = ["#3b82f6", "#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#f59e0b", "#64748b"]

interface SubscriptionsTabProps {
  subscriptions: any
  displayCurrency: string
}

export function SubscriptionsTab({ subscriptions, displayCurrency }: SubscriptionsTabProps) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <div className="flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Abonnements Mensuels</CardTitle>
          </div>
          <CardDescription>Total ce mois: <span className="text-slate-900 font-bold amount-blur">{formatCurrency(subscriptions?.total || 0)}</span></CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            {subscriptions?.items?.map((sub: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-4 border rounded-xl hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 bg-slate-900 rounded-lg flex items-center justify-center text-white text-xs font-bold uppercase">
                    {sub.merchant.substring(0, 2)}
                  </div>
                  <span className="font-medium text-slate-900">{sub.merchant}</span>
                </div>
                <span className="font-bold text-slate-900 amount-blur">{formatCurrency(sub.total)}</span>
              </div>
            ))}
            {(subscriptions?.items?.length ?? 0) === 0 && <p className="text-center text-slate-400 py-10">Aucun abonnement détecté.</p>}
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <CardTitle className="text-lg">Répartition Abonnements</CardTitle>
          <CardDescription>Poids de chaque service.</CardDescription>
        </CardHeader>
        <CardContent className="p-6 h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
              <Pie data={subscriptions?.items || []} cx="50%" cy="50%" innerRadius={80} outerRadius={110} paddingAngle={4} dataKey="total" nameKey="merchant">
                {subscriptions?.items?.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
