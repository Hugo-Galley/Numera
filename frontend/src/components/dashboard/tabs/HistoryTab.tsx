import { History as HistoryIcon, Activity, Layers, Flag } from "lucide-react"
import type { FinancialEvent, Milestone } from "@/components/dashboard/useDashboardData"
import { DecisionJournal } from "@/components/dashboard/DecisionJournal"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import { useIsMobile } from "@/hooks/useIsMobile"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  ReferenceLine
} from "recharts"

// Abréviations usuelles : « juin » et « juil. » se distinguent (les 3 premières lettres donnaient « Jui » deux fois)
const SHORT_MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

interface HistoryTabProps {
  kpiHistory: any[]
  burnRateSeries: any[]
  salarySeries: any[]
  displayCurrency: string
  milestones: Milestone[]
  events: FinancialEvent[]
  onEventsChanged: () => void
  accounts: { id: number; name: string; active?: boolean }[]
}

interface Marker {
  key: string
  label: string  // « m/aaaa », comme les points de kpi-history
  sortKey: string
  period: string
  text: string
}

export function HistoryTab({
  kpiHistory,
  burnRateSeries,
  salarySeries,
  displayCurrency,
  milestones,
  events,
  onEventsChanged,
  accounts
}: HistoryTabProps) {
  // Jalons visibles : faits marquants des mois clôturés + journal des décisions, sur les mois présents
  // sur la courbe (libellé « m/aaaa » de kpi-history ; une décision est rangée dans son mois civil)
  const shownLabels = new Set(kpiHistory.map((p: any) => p.label))
  const markers: Marker[] = [
    ...milestones.map((m) => ({
      key: `closure-${m.year}-${m.month}`,
      label: `${m.month}/${m.year}`,
      sortKey: `${m.year}-${String(m.month).padStart(2, "0")}-00`,
      period: `${SHORT_MONTHS[m.month - 1]} ${m.year}`,
      text: m.highlight ?? "",
    })),
    ...events.map((e) => {
      const [y, mo, d] = e.date.split("-").map(Number)
      return {
        key: `event-${e.id}`,
        label: `${mo}/${y}`,
        sortKey: e.date,
        period: `${d} ${SHORT_MONTHS[mo - 1]} ${y}`,
        text: e.title,
      }
    }),
  ]
  const visibleMilestones = markers
    .filter((m) => shownLabels.has(m.label))
    .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
  const markerLabels = Array.from(new Set(visibleMilestones.map((m) => m.label)))
  const isMobile = useIsMobile()
  const margin = isMobile ? { top: 8, right: 12, left: 0, bottom: 4 } : { top: 40, right: 30, left: 20, bottom: 20 }
  const yWidth = isMobile ? 48 : undefined
  const axisFont = isMobile ? 11 : 12
  return (
    <div className="grid grid-cols-1 gap-5 md:gap-8 lg:grid-cols-2">
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
          <div className="flex items-center gap-2">
            <HistoryIcon className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Flux de trésorerie</CardTitle>
          </div>
          <CardDescription>Revenus vs Dépenses (6 mois).</CardDescription>
        </CardHeader>
        <CardContent className="p-2 pt-4 sm:p-6 h-[280px] md:h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={kpiHistory} margin={margin}>
              <defs>
                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient>
                <linearGradient id="colorDep" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f43f5e" stopOpacity={0.1}/><stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="label" interval="preserveStartEnd" axisLine={false} tickLine={false} tick={{ fontSize: axisFont, fill: '#64748b' }} dy={10} />
              <YAxis width={yWidth} axisLine={false} tickLine={false} tick={{ fontSize: axisFont, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
              <Legend verticalAlign={isMobile ? "bottom" : "top"} height={36} wrapperStyle={isMobile ? { fontSize: 12 } : undefined}/>
              <Area type="monotone" dataKey="revenus" name="Revenus" stroke="#10b981" fill="url(#colorRev)" strokeWidth={3} />
              <Area type="monotone" dataKey="depenses_reelles" name="Dépenses réelles" stroke="#f43f5e" fill="url(#colorDep)" strokeWidth={3} />
              {markerLabels.map((label) => (
                <ReferenceLine
                  key={label}
                  x={label}
                  stroke="#f59e0b"
                  strokeDasharray="4 3"
                  label={{ value: "⚑", position: "top", fill: "#d97706", fontSize: 14 }}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
        {visibleMilestones.length > 0 && (
          <ul className="space-y-1.5 border-t px-4 py-3 md:px-6">
            {visibleMilestones.map((m) => (
              <li key={m.key} className="flex gap-2 text-sm">
                <Flag className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                <span className="shrink-0 font-semibold tabular-nums text-slate-700">{m.period}</span>
                <span className="text-slate-500">{m.text}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Évolution du Burn Rate</CardTitle>
          </div>
          <CardDescription>Dépense moyenne journalière par mois.</CardDescription>
        </CardHeader>
        <CardContent className="p-2 pt-4 sm:p-6 h-[280px] md:h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={burnRateSeries} margin={margin}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="month" 
                axisLine={false} 
                tickLine={false} 
                tickFormatter={(v) => SHORT_MONTHS[v-1] || v} 
                tick={{ fontSize: axisFont, fill: '#64748b' }} 
              />
              <YAxis width={yWidth} axisLine={false} tickLine={false} tick={{ fontSize: axisFont, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => `${v.toFixed(2)}${displayCurrency === 'EUR' ? '€' : displayCurrency} / jour`} />
              <Line type="monotone" dataKey="burn_rate" name="Burn Rate" stroke="#0f172a" strokeWidth={isMobile ? 3 : 4} dot={{ r: isMobile ? 3 : 4, fill: "#0f172a" }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Évolution du Salaire</CardTitle>
          </div>
          <CardDescription>Stabilité et croissance des revenus principaux.</CardDescription>
        </CardHeader>
        <CardContent className="p-2 pt-4 sm:p-6 h-[280px] md:h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={salarySeries} margin={margin}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="month" 
                axisLine={false} 
                tickLine={false} 
                tickFormatter={(v) => SHORT_MONTHS[v-1] || v} 
                tick={{ fontSize: axisFont, fill: '#64748b' }} 
              />
              <YAxis width={yWidth} axisLine={false} tickLine={false} tick={{ fontSize: axisFont, fill: '#64748b' }} tickFormatter={(v) => `${v}${displayCurrency === 'EUR' ? '€' : displayCurrency}`} />
              <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
              <Line type="stepAfter" dataKey="salary" name="Salaire" stroke="#0f172a" strokeWidth={isMobile ? 3 : 4} dot={{ r: isMobile ? 3 : 4, fill: "#0f172a" }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <DecisionJournal events={events} accounts={accounts} onChanged={onEventsChanged} />
    </div>
  )
}
