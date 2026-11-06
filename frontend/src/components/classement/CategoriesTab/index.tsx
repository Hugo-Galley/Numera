import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Archive } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useCategoriesTab } from "./useCategoriesTab"
import { NewCategoryDialog } from "./NewCategoryDialog"
import { CategoriesGrid } from "./CategoriesGrid"
import { EditCategoryDialog } from "./EditCategoryDialog"

export function CategoriesTab() {
  const { t } = useTranslation("classement")
  const ctx = useCategoriesTab()
  const { categories, loading, setShowArchivedCats, showArchivedCats } = ctx
  return (
    <div className="space-y-8 [&_input]:text-base md:[&_input]:text-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h2 className="text-xl md:text-2xl font-bold text-slate-900">{t("index.gestionDesCategories")}</h2>
        
        <NewCategoryDialog ctx={ctx} />
      </div>

      {loading ? (
         <div className="text-center py-20 text-slate-400">{t("index.chargementDeVosCategories")}</div>
      ) : (
        <>
        <CategoriesGrid ctx={ctx} />
        {categories.some((cat) => cat.archived) && (
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={() => setShowArchivedCats((v) => !v)}>
            <Archive className="mr-2 h-4 w-4" />
            {showArchivedCats ? t("index.masquerLesCategoriesArchivees") : i18n.t("misc.showArchived", { ns: "classement", count: categories.filter((cat) => cat.archived).length })}
          </Button>
        )}
        </>
      )}

      {/* Edit Dialog */}
      <EditCategoryDialog ctx={ctx} />
    </div>
  )
}
