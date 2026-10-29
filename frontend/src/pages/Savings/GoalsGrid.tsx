import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Calendar, Info, Layers, Pencil, Tag, Target, Trash2, Zap } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import type { SavingsCtx } from "./useSavings"

/** Cartes des objectifs d'épargne. */
export function GoalsGrid({ ctx }: { ctx: SavingsCtx }) {
  const { accounts, categories, goals, handleDeleteGoal, openEditDialog } = ctx
  return (
    <>
      <div className="grid gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {goals.map((goal) => (
          <Card key={goal.id} className="group overflow-hidden border-slate-100 shadow-sm hover:shadow-md transition-all hover:border-slate-200">
            <CardHeader className="pb-3 flex flex-row items-start justify-between">
              <div className="flex min-w-0 flex-1 gap-3 md:gap-4">
                <div 
                  className="h-12 w-12 rounded-2xl flex items-center justify-center text-white shadow-lg shrink-0"
                  style={{ backgroundColor: goal.color || "rgb(var(--c-slate-900))" }}
                >
                  <Target className="h-6 w-6" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="text-lg font-bold break-words line-clamp-2 md:truncate md:line-clamp-none">{goal.name}</CardTitle>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {goal.deadline && (
                      <Badge variant="secondary" className="text-[9px] uppercase tracking-wider font-bold bg-slate-200 text-slate-700">
                        <Calendar className="h-2.5 w-2.5 mr-1" />
                        {new Date(goal.deadline).toLocaleDateString()}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
              <div className="-mr-2 -mt-1 flex shrink-0 gap-0 opacity-100 transition-opacity md:mr-0 md:mt-0 md:gap-1 md:opacity-0 md:group-hover:opacity-100">
                <Button variant="ghost" size="icon" className="h-10 w-10 rounded-full md:h-8 md:w-8" onClick={() => openEditDialog(goal)} aria-label="Modifier l'objectif">
                  <Pencil className="h-4 w-4 text-slate-400" />
                </Button>
                <Button variant="ghost" size="icon" className="h-10 w-10 rounded-full hover:text-rose-600 md:h-8 md:w-8" onClick={() => handleDeleteGoal(goal.id)} aria-label="Supprimer l'objectif">
                  <Trash2 className="h-4 w-4 text-slate-400" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-end justify-between">
                <div>
                  <p className="whitespace-nowrap text-2xl font-black tabular-nums text-slate-900">{formatCurrency(goal.current_amount)}</p>
                  <p className="text-xs text-slate-500 font-medium">sur {formatCurrency(goal.target_amount)}</p>
                </div>
                <div className="text-right">
                  <div className="flex flex-col items-end">
                    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full mb-1 ${
                      goal.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                      goal.status === 'ahead' ? 'bg-blue-100 text-blue-700' :
                      goal.status === 'behind' ? 'bg-rose-100 text-rose-700' :
                      'bg-slate-100 text-slate-700'
                    }`}>
                      {goal.status === 'completed' ? 'Terminé' :
                       goal.status === 'ahead' ? 'En avance' :
                       goal.status === 'behind' ? 'En retard' : 'Dans les temps'}
                    </span>
                    <p className="text-xl font-black text-slate-900">{Math.round(goal.percentage)}%</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full transition-all duration-1000 rounded-full"
                    style={{ 
                      width: `${Math.min(100, goal.percentage)}%`,
                      backgroundColor: goal.color || "rgb(var(--c-slate-900))"
                    }}
                  />
                </div>
              </div>

              {!!goal.monthly_required && goal.percentage < 100 && (
                <div className="flex flex-wrap items-center justify-between gap-x-2 text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <span className="text-slate-500 font-medium italic">Besoin mensuel recommandé:</span>
                  <span className="whitespace-nowrap font-bold text-slate-900">{formatCurrency(goal.monthly_required)} / mois</span>
                </div>
              )}

              {goal.percentage >= 100 && (
                <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 p-2 rounded-xl text-xs font-bold justify-center border border-emerald-100">
                  <Zap className="h-3 w-3 fill-emerald-600" />
                  Objectif atteint !
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-50">
                 {goal.account_id && (
                   <Badge variant="outline" className="text-[9px] py-0 h-5 bg-white border-slate-200">
                     <Layers className="h-2.5 w-2.5 mr-1 text-slate-400" />
                     {accounts.find(a => a.id === goal.account_id)?.name || "Compte"}
                   </Badge>
                 )}
                 {goal.category_id && (
                   <Badge variant="outline" className="text-[9px] py-0 h-5 bg-white border-slate-200">
                     <Tag className="h-2.5 w-2.5 mr-1 text-slate-400" />
                     {categories.find(c => c.id === goal.category_id)?.name || "Catégorie"}
                   </Badge>
                 )}
                 {goal.keyword && (
                   <Badge variant="outline" className="text-[9px] py-0 h-5 bg-white border-slate-200">
                     <Info className="h-2.5 w-2.5 mr-1 text-slate-400" />
                     TAG: {goal.keyword}
                   </Badge>
                 )}
              </div>
            </CardContent>
          </Card>
        ))}
        {goals.length === 0 && (
          <div className="col-span-full py-16 text-center border-2 border-dashed border-slate-200 rounded-[2rem] bg-slate-50/50">
            <div className="mx-auto h-16 w-16 bg-white rounded-3xl shadow-sm flex items-center justify-center mb-4">
              <Target className="h-8 w-8 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Aucun objectif actif</h3>
            <p className="text-slate-500 text-sm max-w-xs mx-auto mt-2">
              Commencez par créer un objectif pour suivre vos projets financiers.
            </p>
          </div>
        )}
      </div>
    </>
  )
}
