import { useState, useEffect, useMemo } from "react"
import { 
  BarChart3, 
  ArrowUpRight, 
  ArrowDownRight, 
  Minus,
  Calendar,
  Filter,
  ArrowRight
} from "lucide-react"
import { api } from "@/lib/api"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"

export default function Comparison() {
  const [loading, setLoading] = useState(false)
  
  // Period A (Base)
  const [monthA, setMonthA] = useState(String(new Date().getMonth() + 1))
  const [yearA, setYearA] = useState(String(new Date().getFullYear()))
  const [dataA, setDataA] = useState<any>(null)

  // Period B (Comparison)
  const prevDate = new Date()
  prevDate.setMonth(prevDate.getMonth() - 1)
  const [monthB, setMonthB] = useState(String(prevDate.getMonth() + 1))
  const [yearB, setYearB] = useState(String(prevDate.getFullYear()))
  const [dataB, setDataB] = useState<any>(null)

  const months = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
  ]

  const loadComparisonData = async () => {
    setLoading(true)
    try {
      const [resA, resB, catA, catB] = await Promise.all([
        api.get<any>(`/analytics/budget?month=${monthA}&year=${yearA}`),
        api.get<any>(`/analytics/budget?month=${monthB}&year=${yearB}`),
        api.get<any>(`/analytics/expenses-by-category?month=${monthA}&year=${yearA}`),
        api.get<any>(`/analytics/expenses-by-category?month=${monthB}&year=${yearB}`)
      ])
      
      setDataA({ 
        revenus_totaux: resA?.revenus_totaux || 0,
        depenses_totales: resA?.depenses_totales || 0,
        revenus_apres_depenses: resA?.revenus_apres_depenses || 0,
        categories: catA?.items || [] 
      })
      setDataB({ 
        revenus_totaux: resB?.revenus_totaux || 0,
        depenses_totales: resB?.depenses_totales || 0,
        revenus_apres_depenses: resB?.revenus_apres_depenses || 0,
        categories: catB?.items || [] 
      })
    } catch (error) {
      console.error("Comparison load error:", error)
      toast.error("Erreur lors du chargement de la comparaison")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadComparisonData()
  }, [monthA, yearA, monthB, yearB])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value)
  }

  const comparisonRows = useMemo(() => {
    const catsA = dataA?.categories || []
    const catsB = dataB?.categories || []

    const allCategories = new Set<string>()
    catsA.forEach((c: any) => { if (c?.category?.name) allCategories.add(c.category.name) })
    catsB.forEach((c: any) => { if (c?.category?.name) allCategories.add(c.category.name) })

    return Array.from(allCategories).map(catName => {
      const catA = catsA.find((c: any) => c.category.name === catName)
      const catB = catsB.find((c: any) => c.category.name === catName)
      
      const valA = catA?.total || 0
      const valB = catB?.total || 0
      const diff = valA - valB
      const diffPct = valB !== 0 ? (diff / valB) * 100 : 0

      return {
        name: catName,
        color: catA?.category?.color || catB?.category?.color,
        valA,
        valB,
        diff,
        diffPct
      }
    }).sort((a, b) => b.diff - a.diff)
  }, [dataA, dataB])

  return (
    <div className="space-y-8 pb-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Comparaison Mensuelle</h1>
        <p className="text-slate-500 mt-1">Comparez vos revenus et dépenses entre deux périodes.</p>
      </div>

      <div className="flex flex-wrap items-center gap-4 bg-white p-4 rounded-2xl border shadow-sm">
        <div className="flex items-center gap-3">
          <Badge className="bg-slate-900">Période A</Badge>
          <Select value={monthA} onValueChange={setMonthA}>
            <SelectTrigger className="w-[130px]"><SelectValue /></SelectTrigger>
            <SelectContent>{months.map((m, i) => <SelectItem key={i+1} value={String(i+1)}>{m}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={yearA} onValueChange={setYearA}>
            <SelectTrigger className="w-[100px]"><SelectValue /></SelectTrigger>
            <SelectContent>{[2024, 2025, 2026].map(y => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-center w-10">
          <ArrowRight className="text-slate-300" />
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="outline" className="border-slate-300 text-slate-500">Période B</Badge>
          <Select value={monthB} onValueChange={setMonthB}>
            <SelectTrigger className="w-[130px]"><SelectValue /></SelectTrigger>
            <SelectContent>{months.map((m, i) => <SelectItem key={i+1} value={String(i+1)}>{m}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={yearB} onValueChange={setYearB}>
            <SelectTrigger className="w-[100px]"><SelectValue /></SelectTrigger>
            <SelectContent>{[2024, 2025, 2026].map(y => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-2"><CardDescription>Écart Revenus</CardDescription></CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold">
              <span className="amount-blur">
                {dataA && dataB ? formatCurrency(dataA.revenus_totaux - dataB.revenus_totaux) : "-"}
              </span>
            </CardTitle>
            {dataA && dataB && (
              <div className="flex items-center gap-1 mt-1">
                {(dataA.revenus_totaux - dataB.revenus_totaux) >= 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-rose-500" />
                )}
                <span className={`text-xs font-bold ${(dataA.revenus_totaux - dataB.revenus_totaux) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {dataB.revenus_totaux !== 0 ? (((dataA.revenus_totaux - dataB.revenus_totaux) / dataB.revenus_totaux) * 100).toFixed(1) : 0}%
                </span>
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>Écart Dépenses</CardDescription></CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold">
              <span className="amount-blur">
                {dataA && dataB ? formatCurrency(dataA.depenses_totales - dataB.depenses_totales) : "-"}
              </span>
            </CardTitle>
            {dataA && dataB && (
              <div className="flex items-center gap-1 mt-1">
                {(dataA.depenses_totales - dataB.depenses_totales) <= 0 ? (
                  <ArrowDownRight className="h-4 w-4 text-emerald-500" />
                ) : (
                  <ArrowUpRight className="h-4 w-4 text-rose-500" />
                )}
                <span className={`text-xs font-bold ${(dataA.depenses_totales - dataB.depenses_totales) <= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {dataB.depenses_totales !== 0 ? (((dataA.depenses_totales - dataB.depenses_totales) / dataB.depenses_totales) * 100).toFixed(1) : 0}%
                </span>
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>Écart Épargne</CardDescription></CardHeader>
          <CardContent>
            <CardTitle className="text-2xl font-bold">
              <span className="amount-blur">
                {dataA && dataB ? formatCurrency(dataA.revenus_apres_depenses - dataB.revenus_apres_depenses) : "-"}
              </span>
            </CardTitle>
            {dataA && dataB && (
              <div className="flex items-center gap-1 mt-1">
                {(dataA.revenus_apres_depenses - dataB.revenus_apres_depenses) >= 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-rose-500" />
                )}
                <span className={`text-xs font-bold ${(dataA.revenus_apres_depenses - dataB.revenus_apres_depenses) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  Evolution nette
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Détail par catégorie</CardTitle>
          <CardDescription>Variation des dépenses entre les deux périodes.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Catégorie</TableHead>
                  <TableHead className="text-right">{months[parseInt(monthB, 10)-1] || "B"} {yearB}</TableHead>
                  <TableHead className="text-right">{months[parseInt(monthA, 10)-1] || "A"} {yearA}</TableHead>
                  <TableHead className="text-right">Écart</TableHead>
                  <TableHead className="text-right">%</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {comparisonRows.map((row, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full" style={{ backgroundColor: row.color || "#cbd5e1" }} />
                        {row.name}
                      </div>
                    </TableCell>
                    <TableCell className="text-right"><span className="amount-blur">{formatCurrency(row.valB)}</span></TableCell>
                    <TableCell className="text-right"><span className="amount-blur">{formatCurrency(row.valA)}</span></TableCell>
                    <TableCell className={`text-right font-bold ${row.diff > 0 ? "text-rose-600" : row.diff < 0 ? "text-emerald-600" : "text-slate-400"}`}>
                      <div className="flex items-center justify-end gap-1">
                        {row.diff > 0 ? <ArrowUpRight className="h-3 w-3" /> : row.diff < 0 ? <ArrowDownRight className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
                        <span className="amount-blur">{formatCurrency(Math.abs(row.diff))}</span>
                      </div>
                    </TableCell>
                    <TableCell className={`text-right text-xs font-bold ${row.diff > 0 ? "text-rose-500" : row.diff < 0 ? "text-emerald-500" : "text-slate-400"}`}>
                      {row.diffPct > 0 ? "+" : ""}{row.diffPct.toFixed(1)}%
                    </TableCell>
                  </TableRow>
                ))}
                {comparisonRows.length === 0 && !loading && (
                  <TableRow><TableCell colSpan={5} className="text-center py-10 text-slate-400">Sélectionnez deux périodes pour comparer.</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
