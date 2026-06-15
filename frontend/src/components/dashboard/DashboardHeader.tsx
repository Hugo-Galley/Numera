import { useNavigate } from "react-router-dom"
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
}

export function DashboardHeader({
  accounts,
  selectedAccountId,
  setSelectedAccountId,
  month,
  setMonth,
  year,
  setYear
}: DashboardHeaderProps) {
  const navigate = useNavigate()
  const mainAccount = accounts.find(a => a.is_main)

  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
      <div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900">Tableau de bord</h1>
        <p className="text-slate-500 mt-1">Toutes vos analyses financières en un coup d'œil.</p>
      </div>
      <div className="flex flex-wrap items-center gap-2 md:gap-3 bg-white p-1.5 md:p-2 rounded-xl border shadow-sm w-fit">
        <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
          <SelectTrigger className="w-[140px] md:w-[180px] border-none shadow-none focus:ring-0 font-medium h-8 md:h-10">
            <SelectValue placeholder="Comptes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les comptes</SelectItem>
            {accounts.map((acc) => (
              <SelectItem key={acc.id} value={String(acc.id)}>{acc.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Separator orientation="vertical" className="h-6 hidden md:block" />
        <Select value={String(month)} onValueChange={(v: string) => setMonth(Number(v))}>
          <SelectTrigger className="w-[110px] md:w-[130px] border-none shadow-none focus:ring-0 h-8 md:h-10">
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
          <SelectTrigger className="w-[80px] md:w-[100px] border-none shadow-none focus:ring-0 h-8 md:h-10">
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
              className="cursor-pointer flex items-center justify-center px-3 h-8 md:h-10 text-slate-700 border border-slate-200 bg-white hover:bg-slate-50 hover:text-slate-900 font-medium rounded-lg transition-colors text-sm shadow-sm"
              onClick={() => navigate(`/accounts/${mainAccount.id}`)}
            >
              <Star className="h-4 w-4 mr-2 text-slate-400" />
              <span className="truncate max-w-[120px] md:max-w-[150px]">{mainAccount.name}</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
