import { Users } from "lucide-react"
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
  return (
    <Card className="shadow-sm border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b pb-4">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-slate-400" />
          <CardTitle className="text-lg">Top 10 Commerçants</CardTitle>
        </div>
        <CardDescription>Les établissements où vous dépensez le plus.</CardDescription>
      </CardHeader>
      <CardContent className="p-0 sm:p-6 h-[500px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={topMerchants} layout="vertical" margin={{ top: 40, right: 50, left: 50, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis type="number" hide />
            <YAxis dataKey="merchant" type="category" width={150} axisLine={false} tickLine={false} tick={{ fontSize: 12, fontWeight: 500, fill: '#64748b' }} />
            <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(v: number) => formatCurrency(v, displayCurrency)} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
            <Bar dataKey="total" fill="#0f172a" radius={[0, 4, 4, 0]} barSize={30} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
