import { Briefcase } from "lucide-react"
import { PriceChangesNotice } from "@/components/recurring/PriceChangesNotice"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { formatCurrency, formatAmountWithShare } from "@/lib/utils"
import { useIsMobile } from "@/hooks/useIsMobile"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { WorkHours } from "@/components/ui/work-hours"
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
  const isMobile = useIsMobile()
  // Filter out investments & savings, and only show active or potential subscriptions
  const items = (subscriptions?.subscriptions || []).filter((sub: any) => {
    const isInv = sub.category_name === "Investissement" || sub.category_name === "Epargne"
    return !isInv && sub.status !== "paused"
  })

  // Total des abonnements encore prélevés (une récurrence « lapsed » n'est plus débitée depuis deux périodes)
  const total = items
    .filter((item: any) => item.status !== "lapsed")
    .reduce((acc: number, item: any) => acc + (item.monthly_cost || 0), 0)

  return (
    <div className="grid grid-cols-1 gap-5 md:gap-8 lg:grid-cols-2">
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
          <div className="flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Abonnements Mensuels</CardTitle>
          </div>
          <CardDescription>Coût mensuel moyen : <span className="text-slate-900 font-bold amount-blur">{formatCurrency(total, displayCurrency)}</span></CardDescription>
          {displayCurrency === "EUR" && (
            <div className="flex flex-wrap gap-x-3 text-xs text-slate-500">
              <WorkHours amount={total} className="text-xs" />
              <span className="inline-flex items-center gap-1">par an <WorkHours amount={total * 12} className="text-xs" showIcon={false} /></span>
            </div>
          )}
        </CardHeader>
        <CardContent className="p-3 md:p-6">
          <PriceChangesNotice changes={subscriptions?.price_changes} className="mb-4" />
          <div className="space-y-2 md:space-y-4">
            {items.map((sub: any, i: number) => (
              <div key={i} className="flex min-h-14 items-center justify-between gap-3 p-3 md:p-4 border rounded-xl hover:bg-slate-50 transition-colors">
                <div className="flex min-w-0 items-center gap-3">
                  <CompanyLogo name={sub.name} logo={sub.logo} className="h-10 w-10 rounded-lg" />
                  <div className="min-w-0">
                    <span className="block truncate font-medium text-slate-900">{sub.name}</span>
                    {sub.status === "potential" && (
                      <span className="text-[9px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                        Détecté
                      </span>
                    )}
                    {sub.status === "lapsed" && (
                      <span className="text-[9px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                        Plus prélevé ?
                      </span>
                    )}
                  </div>
                </div>
                <span className="shrink-0 whitespace-nowrap tabular-nums font-bold text-slate-900 amount-blur">{formatCurrency(sub.monthly_cost, displayCurrency)}</span>
              </div>
            ))}
            {items.length === 0 && <p className="text-center text-slate-400 py-10">Aucun abonnement détecté.</p>}
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
          <CardTitle className="text-lg">Répartition Abonnements</CardTitle>
          <CardDescription>Poids de chaque service.</CardDescription>
        </CardHeader>
        <CardContent className="p-3 md:p-6 md:h-[400px]">
          <div className="h-[220px] md:h-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
              <Pie data={items} cx="50%" cy="50%" innerRadius={isMobile ? 60 : 80} outerRadius={isMobile ? 85 : 110} paddingAngle={4} dataKey="monthly_cost" nameKey="name">
                {items.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatAmountWithShare(v, items.reduce((s: number, i: any) => s + (i.monthly_cost || 0), 0), displayCurrency)} />
            </PieChart>
          </ResponsiveContainer>
          </div>
          <ul className="mt-3 space-y-1.5 md:hidden">
            {items.map((sub: any, i: number) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                <span className="min-w-0 flex-1 truncate text-slate-600">{sub.name}</span>
                <span className="shrink-0 whitespace-nowrap tabular-nums font-medium text-slate-900 amount-blur">{formatCurrency(sub.monthly_cost, displayCurrency)}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
