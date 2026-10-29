import { formatAmountWithShare, formatCurrency } from "@/lib/utils"
import { toast } from "sonner"
import { useConfirm } from "@/providers/ConfirmProvider"
import { useEffect, useState } from "react"
import { useIsMobile } from "@/hooks/useIsMobile"
import { useSubmit } from "@/hooks/useSubmit"
import { GOAL_COLORS, Resilience } from "./types"
import { getAccounts } from "@/lib/api/accounts"
import { getAnalyticsBudget, getAnalyticsKpiHistory, getAnalyticsResilience } from "@/lib/api/analytics"
import { getCategories } from "@/lib/api/classement"
import { deleteGoalsById, getGoals, patchGoalsById, postGoals } from "@/lib/api/savings"

/** Chargement (période, résilience, historique, objectifs) et actions sur les objectifs d'épargne. */
export function useSavingsData() {
  const confirm = useConfirm()
  const isMobile = useIsMobile()
  const [analytics, setAnalytics] = useState<any>(null)
  const [resilience, setResilience] = useState<Resilience | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [goals, setGoals] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  
  const [month, setMonth] = useState<string>(String(new Date().getMonth() + 1))
  const [year, setYear] = useState<string>(String(new Date().getFullYear()))
  const [period, setPeriod] = useState<"monthly" | "all-time">("monthly")

  // Form state
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingGoal, setEditingGoal] = useState<any>(null)
  const [goalForm, setGoalForm] = useState({
    name: "",
    target_amount: "",
    keyword: "",
    color: GOAL_COLORS[0],
    deadline: "",
    account_id: "none",
    category_id: "none"
  })

  const loadData = async () => {
    setLoading(true)
    setLoadFailed(false)
    try {
      const queryParams = period === "monthly" 
        ? `month=${month}&year=${year}`
        : ""
      
      const now = new Date()
      const [budget, kpiHistory, goalsData, accs, cats, resilienceData] = await Promise.all([
        getAnalyticsBudget<any>(`?${queryParams}`),
        getAnalyticsKpiHistory<any[]>("?months_count=12"),
        getGoals<any[]>(),
        getAccounts<any[]>(),
        getCategories<any[]>("?include_archived=false"),
        getAnalyticsResilience<Resilience>(period === "monthly"
          ? `?month=${month}&year=${year}`
          : `?month=${now.getMonth() + 1}&year=${now.getFullYear()}`),
      ])
      setAnalytics(budget)
      setResilience(resilienceData)
      setHistory(kpiHistory)
      setGoals(goalsData)
      setAccounts(accs)
      setCategories(cats)
    } catch (error) {
      console.error("Failed to load savings data", error)
      setLoadFailed(true)
      toast.error("Impossible de charger les données d'épargne")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [month, year, period])

  const [handleCreateOrUpdateGoal, handleCreateOrUpdateGoalBusy] = useSubmit(async () => {
    if (!goalForm.name || !goalForm.target_amount) {
      toast.error("Veuillez remplir les champs obligatoires (Nom et Montant)")
      return
    }

    try {
      const payload: any = {
        name: goalForm.name,
        target_amount: parseFloat(goalForm.target_amount),
        keyword: goalForm.keyword || null,
        color: goalForm.color,
        icon: "Target", 
        deadline: goalForm.deadline || null,
        account_id: goalForm.account_id === "none" ? null : parseInt(goalForm.account_id),
        category_id: goalForm.category_id === "none" ? null : parseInt(goalForm.category_id)
      }

      if (editingGoal) {
        await patchGoalsById(editingGoal.id, payload)
        toast.success("Objectif mis à jour")
      } else {
        await postGoals(payload)
        toast.success("Objectif créé")
      }
      setIsDialogOpen(false)
      setEditingGoal(null)
      setGoalForm({ name: "", target_amount: "", keyword: "", color: GOAL_COLORS[0], deadline: "", account_id: "none", category_id: "none" })
      loadData()
    } catch (error) {
      console.error("Error saving goal:", error)
      toast.error("Une erreur est survenue lors de l'enregistrement")
    }
  })

  const handleDeleteGoal = async (id: number) => {
    if (!(await confirm("Supprimer cet objectif ?"))) return
    try {
      await deleteGoalsById(id)
      toast.success("Objectif supprimé")
      loadData()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  const openEditDialog = (goal: any) => {
    setEditingGoal(goal)
    setGoalForm({
      name: goal.name,
      target_amount: String(goal.target_amount),
      keyword: goal.keyword || "",
      color: goal.color || GOAL_COLORS[0],
      deadline: goal.deadline || "",
      account_id: goal.account_id ? String(goal.account_id) : "none",
      category_id: goal.category_id ? String(goal.category_id) : "none"
    })
    setIsDialogOpen(true)
  }

  // Montant + part du total des composantes positives ; pas de part pour une valeur négative.
  const shareLabel = (v: number, payload: any, keys: string[]) => {
    if (v <= 0) return formatCurrency(v)
    const total = keys.reduce((s, k) => s + Math.max(0, Number(payload?.[k]) || 0), 0)
    return formatAmountWithShare(v, total)
  }

  const savingsRate = analytics?.taux_epargne || 0
  const hasIncome = (analytics?.revenus_totaux ?? 0) >= 1
  
  const getRateColor = (rate: number) => {
    if (rate >= 30) return "text-emerald-600"
    if (rate >= 15) return "text-blue-600"
    if (rate >= 0) return "text-amber-600"
    return "text-rose-600"
  }

  const months = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
  ]


  return { confirm, isMobile, analytics, setAnalytics, resilience, setResilience, history, setHistory, goals, setGoals, accounts, setAccounts, categories, setCategories, loading, setLoading, loadFailed, setLoadFailed, month, setMonth, year, setYear, period, setPeriod, isDialogOpen, setIsDialogOpen, editingGoal, setEditingGoal, goalForm, setGoalForm, loadData, handleCreateOrUpdateGoal, handleCreateOrUpdateGoalBusy, handleDeleteGoal, openEditDialog, shareLabel, savingsRate, hasIncome, getRateColor, months }
}
