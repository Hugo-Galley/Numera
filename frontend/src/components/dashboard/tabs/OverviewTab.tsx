import { useState, useMemo } from "react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tag, Wallet, PiggyBank, TrendingUp } from "lucide-react"
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine
} from "recharts"
import { SankeyFlow } from "@/components/analytics/SankeyFlow"
import { formatCurrency } from "@/lib/utils"
import { IconComponent } from "../IconComponent"

const COLORS = ["#3b82f6", "#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#f59e0b", "#64748b"]

interface OverviewTabProps {
  sankeyData: any
  expensesByCategory: any[]
  displayCurrency: string
  tagTotals: any[]
  patrimoineAllocation: any
}

export function OverviewTab({
  sankeyData,
  expensesByCategory,
  displayCurrency,
  tagTotals,
  patrimoineAllocation
}: OverviewTabProps) {
  const [groupBy, setGroupBy] = useState<"account" | "category" | "mixed" | "institution">("mixed")

  const flatItems = useMemo(() => {
    if (!patrimoineAllocation?.items) return []
    const total = patrimoineAllocation.total_patrimoine || 1
    return patrimoineAllocation.items.map((item: any, i: number) => ({
      id: `${item.account_id}-${item.account_name}`,
      name: item.account_name,
      type: item.type,
      balance_eur: item.balance_eur,
      percentage: Number(((item.balance_eur / total) * 100).toFixed(2)),
      color: COLORS[i % COLORS.length],
      original_item: item
    }))
  }, [patrimoineAllocation])

  const groupedItems = useMemo(() => {
    if (!patrimoineAllocation?.items) return {}
    const groups: Record<string, { total_eur: number; items: any[] }> = {
      courant: { total_eur: 0, items: [] },
      epargne: { total_eur: 0, items: [] },
      investissement: { total_eur: 0, items: [] }
    }
    
    patrimoineAllocation.items.forEach((item: any) => {
      const type = item.type || "courant"
      if (!groups[type]) {
        groups[type] = { total_eur: 0, items: [] }
      }
      groups[type].items.push(item)
      groups[type].total_eur += item.balance_eur
    })
    
    return groups
  }, [patrimoineAllocation])

  const CATEGORY_COLORS: Record<string, string> = {
    courant: "#3b82f6", // Blue
    epargne: "#10b981", // Emerald
    investissement: "#6366f1" // Indigo
  }

  const CATEGORY_LABELS: Record<string, string> = {
    courant: "Comptes Courants",
    epargne: "Épargne",
    investissement: "Investissements"
  }

  const categoryData = useMemo(() => {
    const total = patrimoineAllocation?.total_patrimoine || 0
    return [
      {
        name: "Comptes Courants",
        type: "courant",
        value: groupedItems.courant?.total_eur || 0,
        percentage: total > 0 ? Number(((groupedItems.courant?.total_eur || 0) / total * 100).toFixed(2)) : 0,
        color: CATEGORY_COLORS.courant,
      },
      {
        name: "Épargne",
        type: "epargne",
        value: groupedItems.epargne?.total_eur || 0,
        percentage: total > 0 ? Number(((groupedItems.epargne?.total_eur || 0) / total * 100).toFixed(2)) : 0,
        color: CATEGORY_COLORS.epargne,
      },
      {
        name: "Investissements",
        type: "investissement",
        value: groupedItems.investissement?.total_eur || 0,
        percentage: total > 0 ? Number(((groupedItems.investissement?.total_eur || 0) / total * 100).toFixed(2)) : 0,
        color: CATEGORY_COLORS.investissement,
      },
    ].filter(cat => cat.value > 0)
  }, [groupedItems, patrimoineAllocation])

  const mixedItems = useMemo(() => {
    if (!patrimoineAllocation?.items) return []
    
    let totalCourant = 0
    let totalEpargne = 0
    const list: any[] = []
    
    patrimoineAllocation.items.forEach((item: any) => {
      if (item.type === "courant") {
        totalCourant += item.balance_eur
      } else if (item.type === "epargne") {
        totalEpargne += item.balance_eur
      } else {
        list.push({
          id: `${item.account_id}-${item.account_name}`,
          name: item.account_name,
          type: item.type,
          balance_eur: item.balance_eur,
          original_item: item
        })
      }
    })
    
    const result: any[] = []
    if (totalCourant > 0) {
      result.push({
        id: "group-courant",
        name: "Comptes Courants",
        type: "courant",
        balance_eur: totalCourant,
        isGroup: true,
        color: "#3b82f6" // blue
      })
    }
    
    if (totalEpargne > 0) {
      result.push({
        id: "group-epargne",
        name: "Épargne",
        type: "epargne",
        balance_eur: totalEpargne,
        isGroup: true,
        color: "#10b981" // emerald
      })
    }
    
    list.forEach((item, index) => {
      item.color = COLORS[(index + 2) % COLORS.length]
      result.push(item)
    })
    
    const total = patrimoineAllocation.total_patrimoine || 1
    result.forEach(item => {
      item.percentage = Number(((item.balance_eur / total) * 100).toFixed(2))
    })
    
    result.sort((a, b) => b.balance_eur - a.balance_eur)
    
    return result
  }, [patrimoineAllocation])

  const institutionData = useMemo(() => {
    if (!patrimoineAllocation?.items) return []
    const total = patrimoineAllocation.total_patrimoine || 1
    
    // Group accounts by institution name
    const grouped: Record<string, { name: string; value: number; items: any[] }> = {}
    
    patrimoineAllocation.items.forEach((item: any) => {
      const instName = item.institution ? item.institution.trim() : "Autre / Non spécifié"
      if (!grouped[instName]) {
        grouped[instName] = {
          name: instName,
          value: 0,
          items: []
        }
      }
      grouped[instName].value += item.balance_eur
      grouped[instName].items.push(item)
    })
    
    // Convert to array and calculate percentage & color
    return Object.values(grouped)
      .sort((a, b) => b.value - a.value)
      .map((group, index) => ({
        ...group,
        percentage: Number(((group.value / total) * 100).toFixed(2)),
        color: COLORS[index % COLORS.length]
      }))
  }, [patrimoineAllocation])

  const chartData = 
    groupBy === "category" 
      ? categoryData 
      : groupBy === "account" 
      ? flatItems 
      : groupBy === "institution" 
      ? institutionData 
      : mixedItems

  const chartDataKey = groupBy === "category" || groupBy === "institution" ? "value" : "balance_eur"

  return (
    <div className="space-y-8">
      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4">
          <CardTitle className="text-lg">Flux Financiers</CardTitle>
          <CardDescription>Visualisation des revenus vers les dépenses et l'épargne.</CardDescription>
        </CardHeader>
        <CardContent className="p-6 h-[600px]">
          <SankeyFlow data={sankeyData} currency={displayCurrency} />
        </CardContent>
      </Card>

      <Card className="shadow-sm border-slate-100 overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <CardTitle className="text-lg">Répartition du Patrimoine</CardTitle>
            <CardDescription>
              Distribution de vos actifs sur l'ensemble de vos comptes actifs.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-4 self-start md:self-auto">
            {/* View Mode Toggle */}
            <Tabs value={groupBy} onValueChange={(v) => setGroupBy(v as any)} className="w-auto">
              <TabsList className="bg-slate-100 border border-slate-200/50 p-1 rounded-xl">
                <TabsTrigger value="category" className="rounded-lg text-xs font-semibold px-3 py-1">Par Catégorie</TabsTrigger>
                <TabsTrigger value="mixed" className="rounded-lg text-xs font-semibold px-3 py-1">Mixte</TabsTrigger>
                <TabsTrigger value="account" className="rounded-lg text-xs font-semibold px-3 py-1">Par Compte</TabsTrigger>
                <TabsTrigger value="institution" className="rounded-lg text-xs font-semibold px-3 py-1">Par Établissement</TabsTrigger>
              </TabsList>
            </Tabs>
            <span className="text-sm font-semibold text-slate-500 bg-slate-100/80 px-3 py-1 rounded-lg">
              Total : <span className="amount-blur text-slate-900 font-bold">{formatCurrency(patrimoineAllocation?.total_patrimoine || 0, "EUR")}</span>
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {(!patrimoineAllocation || !patrimoineAllocation.items || patrimoineAllocation.items.length === 0) ? (
            <div className="text-center py-8 text-slate-400">Aucune donnée de patrimoine disponible.</div>
          ) : (
            <div className="grid gap-8 lg:grid-cols-12 items-center">
              {/* Camembert (PieChart) */}
              <div className="lg:col-span-5 h-[300px] flex items-center justify-center relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={75}
                      outerRadius={100}
                      paddingAngle={3}
                      dataKey={chartDataKey}
                      nameKey="name"
                    >
                      {chartData.map((item: any, i: number) => (
                        <Cell key={i} fill={item.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} 
                      formatter={(v: number) => formatCurrency(v, "EUR")} 
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Center Text (Total) */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Patrimoine</span>
                  <span className="text-lg font-black text-slate-800 amount-blur">
                    {formatCurrency(patrimoineAllocation.total_patrimoine, "EUR")}
                  </span>
                </div>
              </div>

              {/* Grouped, Mixed or Flat Details List */}
              <div className="lg:col-span-7 space-y-4 max-h-[300px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-200">
                {groupBy === "category" ? (
                  Object.entries(groupedItems).map(([type, group]: [string, any]) => {
                    if (group.items.length === 0) return null;
                    const catLabel = CATEGORY_LABELS[type] || type;
                    const catColor = CATEGORY_COLORS[type] || "#64748b";
                    const totalPatrimoine = patrimoineAllocation.total_patrimoine || 1;
                    const catPercentage = ((group.total_eur / totalPatrimoine) * 100).toFixed(1);
                    
                    return (
                      <div key={type} className="space-y-2">
                        {/* Group Header */}
                        <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 px-1 bg-slate-50/30">
                          <span className="text-xs font-black tracking-wider text-slate-500 uppercase">
                            {catLabel}
                          </span>
                          <div className="text-right">
                            <span className="text-xs font-extrabold text-slate-700 amount-blur">
                              {formatCurrency(group.total_eur, "EUR")}
                            </span>
                            <span className="text-[10px] text-slate-400 font-semibold ml-2">
                              {catPercentage}%
                            </span>
                          </div>
                        </div>

                        {/* Accounts in Group */}
                        <div className="space-y-1.5">
                          {group.items.map((item: any) => (
                            <div 
                              key={`${item.account_id}-${item.account_name}`} 
                              className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
                            >
                              <div className="flex items-center gap-2.5">
                                <div 
                                  className="h-2 w-2 rounded-full flex-shrink-0" 
                                  style={{ backgroundColor: catColor }} 
                                />
                                <div>
                                  <span className="font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                                    {item.account_name}
                                  </span>
                                  {item.currency !== "EUR" && (
                                    <span className="text-[10px] text-slate-400 font-medium block">
                                      Original: {formatCurrency(item.balance, item.currency)}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <span className="font-bold text-sm text-slate-900 block amount-blur">
                                  {formatCurrency(item.balance_eur, "EUR")}
                                </span>
                                <span className="text-[10px] font-medium text-slate-400">
                                  {((item.balance_eur / totalPatrimoine) * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })
                ) : groupBy === "institution" ? (
                  institutionData.map((group: any) => {
                    const totalPatrimoine = patrimoineAllocation.total_patrimoine || 1;
                    return (
                      <div key={group.name} className="space-y-2">
                        {/* Group Header */}
                        <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 px-1 bg-slate-50/30">
                          <span className="text-xs font-black tracking-wider text-slate-500 uppercase">
                            {group.name}
                          </span>
                          <div className="text-right">
                            <span className="text-xs font-extrabold text-slate-700 amount-blur">
                              {formatCurrency(group.value, "EUR")}
                            </span>
                            <span className="text-[10px] text-slate-400 font-semibold ml-2">
                              {group.percentage}%
                            </span>
                          </div>
                        </div>

                        {/* Accounts in Group */}
                        <div className="space-y-1.5">
                          {group.items.map((item: any) => (
                            <div 
                              key={`${item.account_id}-${item.account_name}`} 
                              className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
                            >
                              <div className="flex items-center gap-2.5">
                                <div 
                                  className="h-2 w-2 rounded-full flex-shrink-0" 
                                  style={{ backgroundColor: group.color }} 
                                />
                                <div>
                                  <span className="font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                                    {item.account_name}
                                  </span>
                                  {item.currency !== "EUR" && (
                                    <span className="text-[10px] text-slate-400 font-medium block">
                                      Original: {formatCurrency(item.balance, item.currency)}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <span className="font-bold text-sm text-slate-900 block amount-blur">
                                  {formatCurrency(item.balance_eur, "EUR")}
                                </span>
                                <span className="text-[10px] font-medium text-slate-400">
                                  {((item.balance_eur / totalPatrimoine) * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })
                ) : groupBy === "mixed" ? (
                  mixedItems.map((item: any) => (
                    <div 
                      key={item.id} 
                      className="flex items-center justify-between p-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
                    >
                      <div className="flex items-center gap-3">
                        <div 
                          className="h-3 w-3 rounded-full flex-shrink-0" 
                          style={{ backgroundColor: item.color }} 
                        />
                        <div>
                          <span className="font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                            {item.name}
                          </span>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                              {item.type === "courant" ? "Courant" : item.type === "epargne" ? "Épargne" : "Investissement"}
                            </span>
                            {item.original_item && item.original_item.currency !== "EUR" && (
                              <span className="text-[10px] text-slate-400 font-medium">
                                Original: {formatCurrency(item.original_item.balance, item.original_item.currency)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-sm text-slate-900 block amount-blur">
                          {formatCurrency(item.balance_eur, "EUR")}
                        </span>
                        <span className="text-[11px] font-medium text-slate-400">
                          {item.percentage}%
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  flatItems.map((item: any) => (
                    <div 
                      key={item.id} 
                      className="flex items-center justify-between p-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
                    >
                      <div className="flex items-center gap-3">
                        <div 
                          className="h-3 w-3 rounded-full flex-shrink-0" 
                          style={{ backgroundColor: item.color }} 
                        />
                        <div>
                          <span className="font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                            {item.name}
                          </span>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                              {item.type === "courant" ? "Courant" : item.type === "epargne" ? "Épargne" : "Investissement"}
                            </span>
                            {item.original_item && item.original_item.currency !== "EUR" && (
                              <span className="text-[10px] text-slate-400 font-medium">
                                Original: {formatCurrency(item.original_item.balance, item.original_item.currency)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-sm text-slate-900 block amount-blur">
                          {formatCurrency(item.balance_eur, "EUR")}
                        </span>
                        <span className="text-[11px] font-medium text-slate-400">
                          {item.percentage}%
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-8 lg:grid-cols-12">
        <Card className="lg:col-span-8 shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <CardTitle className="text-lg">Dépenses par catégorie</CardTitle>
            <CardDescription>Où va votre argent ce mois-ci ?</CardDescription>
          </CardHeader>
          <CardContent className="p-0 sm:p-6 h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={expensesByCategory} layout="vertical" margin={{ top: 40, right: 40, left: 40, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis type="number" hide />
                <YAxis dataKey="category.name" type="category" width={100} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                <Bar dataKey="total" radius={[0, 4, 4, 0]} barSize={20}>
                  {expensesByCategory.map((item, i) => (
                    <Cell key={i} fill={item.category.color || COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
                {expensesByCategory
                  .filter(item => item.category?.monthly_limit != null)
                  .map((item, i) => (
                    <ReferenceLine
                      key={`limit-${i}`}
                      x={item.category.monthly_limit}
                      yAxisId={0}
                      stroke="#f59e0b"
                      strokeDasharray="4 3"
                      strokeWidth={1.5}
                    />
                  ))}
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="lg:col-span-4 shadow-sm border-slate-100 overflow-hidden">
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <CardTitle className="text-lg">Répartition</CardTitle>
            <CardDescription>Poids des catégories.</CardDescription>
          </CardHeader>
          <CardContent className="p-6 flex flex-col items-center">
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                  <Pie data={expensesByCategory} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={4} dataKey="total" nameKey="category.name">
                    {expensesByCategory.map((item, i) => <Cell key={i} fill={item.category.color || COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} formatter={(v: number) => formatCurrency(v, displayCurrency)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-full space-y-3 mt-4">
               {expensesByCategory.slice(0, 4).map((item, i) => (
                 <div key={i} className="flex justify-between text-sm">
                   <span className="text-slate-500 flex items-center gap-2">
                     <div className="h-4 w-4 rounded-lg flex items-center justify-center" style={{ backgroundColor: item.category.color || COLORS[i % COLORS.length] }}>
                       <IconComponent name={item.category.icon} className="h-2 w-2 text-white" />
                     </div>
                     {item.category.name}
                   </span>
                   <span className="font-bold">
                     <span className="amount-blur">{item.percentage}%</span>
                   </span>
                 </div>
               ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {tagTotals.length > 0 && (
        <Card className="shadow-sm border-slate-100 overflow-hidden mt-8">
          <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Projets & Contextes (Tags)</CardTitle>
              <CardDescription>Dépenses transverses sur la période.</CardDescription>
            </div>
            <Tag className="h-5 w-5 text-slate-400" />
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex flex-wrap gap-4">
              {tagTotals.map((t) => (
                <div key={t.id} className="flex items-center gap-3 p-3 px-4 bg-white border border-slate-200 rounded-full shadow-sm hover:border-slate-300 transition-colors group">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: t.color || "#64748b" }} />
                  <div>
                    <p className="text-[11px] font-medium text-slate-500 leading-none mb-1">{t.name}</p>
                    <p className="text-sm font-bold text-slate-900 leading-none">{formatCurrency(t.total_eur, "EUR")}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
