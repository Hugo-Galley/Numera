import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Tag, Target } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { GOAL_COLORS } from "./types"
import type { SavingsCtx } from "./useSavings"

/** En-tête des objectifs et dialogue de création / modification. */
export function GoalsHeader({ ctx }: { ctx: SavingsCtx }) {
  const { accounts, categories, editingGoal, goalForm, handleCreateOrUpdateGoal, handleCreateOrUpdateGoalBusy, isDialogOpen, setEditingGoal, setGoalForm, setIsDialogOpen } = ctx
  return (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3 md:gap-4 md:pb-2">
        <div className="flex items-center gap-2">
          <Target className="h-5 w-5 text-slate-400" />
          <h2 className="text-xl font-bold text-slate-900">Mes Objectifs</h2>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open)
          if (!open) {
            setEditingGoal(null)
            setGoalForm({ name: "", target_amount: "", keyword: "", color: GOAL_COLORS[0], deadline: "", account_id: "none", category_id: "none" })
          }
        }}>
          <DialogTrigger asChild>
            <Button className="h-11 w-full rounded-xl shadow-sm sm:h-10 sm:w-auto">
              <Plus className="h-4 w-4 mr-2" />
              Nouvel Objectif
            </Button>
          </DialogTrigger>
          <DialogContent className="rounded-2xl sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>{editingGoal ? "Modifier l'objectif" : "Créer un objectif"}</DialogTitle>
              <DialogDescription>
                Liez votre objectif à un mot-clé, un compte ou une catégorie pour suivre l'accumulation.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="name">Nom de l'objectif</Label>
                  <Input 
                    id="name" 
                    placeholder="ex: Vacances Japon" 
                    value={goalForm.name}
                    onChange={(e) => setGoalForm({ ...goalForm, name: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="target">Montant cible (€)</Label>
                  <Input 
                    id="target" 
                    type="number" inputMode="decimal" 
                    placeholder="5000" 
                    value={goalForm.target_amount}
                    onChange={(e) => setGoalForm({ ...goalForm, target_amount: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label>Lier à un compte (optionnel)</Label>
                  <Select value={goalForm.account_id} onValueChange={(v) => setGoalForm({ ...goalForm, account_id: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choisir un compte" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Aucun compte</SelectItem>
                      {accounts.map(acc => (
                        <SelectItem key={acc.id} value={String(acc.id)}>{acc.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label>Lier à une catégorie (optionnel)</Label>
                  <Select value={goalForm.category_id} onValueChange={(v) => setGoalForm({ ...goalForm, category_id: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choisir une catégorie" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Aucune catégorie</SelectItem>
                      {categories.map(cat => (
                        <SelectItem key={cat.id} value={String(cat.id)}>{cat.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="keyword">Mot-clé Tag (optionnel)</Label>
                  <Input 
                    id="keyword" 
                    placeholder="ex: japon" 
                    value={goalForm.keyword}
                    onChange={(e) => setGoalForm({ ...goalForm, keyword: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="deadline">Date cible (optionnel)</Label>
                  <Input 
                    id="deadline" 
                    type="date" 
                    value={goalForm.deadline}
                    onChange={(e) => setGoalForm({ ...goalForm, deadline: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label>Couleur</Label>
                <div className="flex flex-wrap gap-2">
                  {GOAL_COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      className={`h-10 w-10 rounded-full border-2 transition-all md:h-8 md:w-8 ${goalForm.color === c ? 'border-slate-900 scale-110 shadow-md' : 'border-transparent'}`}
                      style={{ backgroundColor: c }}
                      onClick={() => setGoalForm({ ...goalForm, color: c })}
                      aria-label={`Couleur ${c}`}
                    />
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={() => handleCreateOrUpdateGoal()} disabled={handleCreateOrUpdateGoalBusy} className="h-11 w-full rounded-xl sm:h-10">
                {editingGoal ? "Mettre à jour" : "Créer l'objectif"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  )
}
