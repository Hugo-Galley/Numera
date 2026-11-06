import { useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { SalaryManager } from "@/components/tools/SalaryManager"
import { BenefitsSection } from "./BenefitsSection"

const VIEWS = ["salaire", "aides"] as const

// Onglet « Salaire » des Échéances : salaire ou aides perçues (?vue=aides, lien du Centre d'Actions)
export function IncomeTab() {
  const { t } = useTranslation("recurring")
  const [searchParams, setSearchParams] = useSearchParams()
  const view = searchParams.get("vue") === "aides" ? "aides" : "salaire"
  const setView = (value: string) =>
    setSearchParams((params) => {
      if (value === "aides") params.set("vue", value)
      else params.delete("vue")
      return params
    }, { replace: true })

  return (
    <div className="space-y-6">
      <div className="flex w-fit items-center gap-1 rounded-xl bg-slate-100 p-1">
        {VIEWS.map((view_) => (
          <Button
            key={view_}
            variant={view === view_ ? "white" : "ghost"}
            size="sm"
            className={`h-9 rounded-lg px-4 text-xs font-bold ${view === view_ ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
            onClick={() => setView(view_)}
          >
            {t(`incomeTab.${view_}`)}
          </Button>
        ))}
      </div>
      {view === "aides" ? <BenefitsSection /> : <SalaryManager />}
    </div>
  )
}
