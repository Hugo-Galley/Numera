import { useNavigate } from "react-router-dom"
import { AccountLogo } from "@/components/ui/AccountLogo"
import { Star } from "lucide-react"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"

const months = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

interface DashboardHeaderProps {
  accounts: any[]
  selectedAccountId: string
  setSelectedAccountId: (v: string) => void
  month: number
  setMonth: (v: number) => void
  year: number
  setYear: (v: number) => void
  periodRange?: string | null
}

export function DashboardHeader({
  accounts,
  selectedAccountId,
  setSelectedAccountId,
  month,
  setMonth,
  year,
  setYear,
  periodRange
}: DashboardHeaderProps) {
  const navigate = useNavigate()
  const mainAccount = accounts.find(a => a.is_main)

  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 md:gap-6">
      <div className="min-w-0">
        <h1 className="text-2xl md:text-4xl font-extrabold tracking-tight text-slate-900">Tableau de bord</h1>
        <p className="hidden sm:block text-slate-500 mt-1">Toutes vos analyses financières en un coup d'œil.</p>
        {periodRange && (
          <span className="mt-1.5 md:mt-2 inline-flex items-center whitespace-nowrap rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-xs font-medium text-slate-500">
            Période de paie : {periodRange}
          </span>
        )}
      </div>
      <div className="grid grid-cols-[1fr_auto] gap-2 sm:flex sm:flex-wrap sm:items-center md:gap-3 bg-white p-2 rounded-xl border shadow-sm w-full sm:w-fit">
        <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
          <SelectTrigger className="col-span-2 w-full sm:w-[160px] md:w-[180px] border-slate-200 sm:border-none shadow-none focus:ring-0 font-medium h-11 md:h-10 text-base md:text-sm">
            <SelectValue placeholder="Comptes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les comptes</SelectItem>
            {accounts.filter((acc) => acc.active).map((acc) => (
              <SelectItem key={acc.id} value={String(acc.id)}>
                <span className="flex items-center gap-2"><AccountLogo accountId={acc.id} className="h-5 w-5" />{acc.name}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Separator orientation="vertical" className="h-6 hidden md:block" />
        <Select value={String(month)} onValueChange={(v: string) => setMonth(Number(v))}>
          <SelectTrigger className="w-full sm:w-[120px] md:w-[130px] border-slate-200 sm:border-none shadow-none focus:ring-0 h-11 md:h-10 text-base md:text-sm">
            <SelectValue placeholder="Mois" />
          </SelectTrigger>
          <SelectContent>
            {months.map((m, i) => (
              <SelectItem key={i + 1} value={String(i + 1)}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Separator orientation="vertical" className="h-6 hidden md:block" />
        <Select value={String(year)} onValueChange={(v: string) => setYear(Number(v))}>
          <SelectTrigger className="w-[96px] sm:w-[90px] md:w-[100px] border-slate-200 sm:border-none shadow-none focus:ring-0 h-11 md:h-10 text-base md:text-sm">
            <SelectValue placeholder="Année" />
          </SelectTrigger>
          <SelectContent>
            {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i).map((y) => (
              <SelectItem key={y} value={String(y)}>{y}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {mainAccount && (
          <>
            <Separator orientation="vertical" className="h-6 hidden md:block" />
            <div 
              className="col-span-2 cursor-pointer flex items-center justify-center px-3 h-11 md:h-10 text-slate-700 border border-slate-200 bg-white hover:bg-slate-50 hover:text-slate-900 font-medium rounded-lg transition-colors text-sm shadow-sm"
              onClick={() => navigate(`/accounts/${mainAccount.id}`)}
            >
              <Star className="h-4 w-4 mr-2 text-slate-400" />
              <span className="truncate max-w-[240px] sm:max-w-[120px] md:max-w-[150px]">{mainAccount.name}</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
