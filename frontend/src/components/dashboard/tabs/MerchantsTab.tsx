import { Users } from "lucide-react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { formatAmountWithShare } from "@/lib/utils"
import { formatWorkDuration } from "@/components/ui/work-hours"
import { useIsMobile } from "@/hooks/useIsMobile"
import { useWorkTime } from "@/providers/WorkTimeProvider"
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from "recharts"

interface MerchantsTabProps {
  topMerchants: any[]
  displayCurrency: string
}

export function MerchantsTab({ topMerchants, displayCurrency }: MerchantsTabProps) {
  const isMobile = useIsMobile()
  const { workTime } = useWorkTime()
  const rate = displayCurrency === "EUR" ? workTime?.hourly_rate : null
  const formatTooltip = (v: number) => {
    const amount = formatAmountWithShare(v, topMerchants.reduce((s: number, m: any) => s + (m.total || 0), 0), displayCurrency)
    return rate ? `${amount} (≈ ${formatWorkDuration(v / rate, workTime!.work_hours_per_day)} de travail)` : amount
  }

  return (
    <Card className="shadow-sm border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-slate-400" />
          <CardTitle className="text-lg">Top 10 Commerçants</CardTitle>
        </div>
        <CardDescription>Les établissements où vous dépensez le plus.</CardDescription>
      </CardHeader>
      <CardContent className="p-2 pt-4 sm:p-6" style={{ height: isMobile ? Math.max(240, topMerchants.length * 36 + 24) : 500 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={topMerchants} layout="vertical" margin={isMobile ? { top: 4, right: 12, left: 0, bottom: 4 } : { top: 40, right: 50, left: 50, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis type="number" hide />
            <YAxis dataKey="merchant" type="category" width={isMobile ? 104 : 150} axisLine={false} tickLine={false} tick={{ fontSize: isMobile ? 11 : 12, fontWeight: 500, fill: '#64748b' }} tickFormatter={(v: string) => (isMobile && v.length > 16 ? `${v.slice(0, 15)}…` : v)} />
            <Tooltip cursor={{ fill: '#f8fafc' }} formatter={formatTooltip} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
            <Bar dataKey="total" fill="#0f172a" radius={[0, 4, 4, 0]} barSize={isMobile ? 18 : 30} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
