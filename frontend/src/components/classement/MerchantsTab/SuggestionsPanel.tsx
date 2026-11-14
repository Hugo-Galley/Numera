import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { AlertCircle, PlusCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { MerchantsTabCtx } from "./useMerchantsTab"

/** Suggestions de marchands à normaliser. */
export function SuggestionsPanel({ ctx }: { ctx: MerchantsTabCtx }) {
  const { t } = useTranslation("classement")
  const { setNewAliases, setNewName, setNewOpen, suggestions } = ctx
  return (
    <>
      <div className="space-y-6">
        <Card className="border-amber-100 bg-amber-50/30">
          <CardHeader>
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-amber-900">
              <AlertCircle className="h-4 w-4" /> {t("suggestionsPanel.suggestions")}
            </CardTitle>
            <CardDescription className="text-xs">{t("suggestionsPanel.libellesFrequentsNonNormalises")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {suggestions.map((s, i) => (
              <div key={i} className="flex items-center justify-between gap-2 p-2 bg-white rounded-lg border border-amber-100 shadow-xs">
                <div className="min-w-0">
                  <p className="text-xs font-bold text-slate-900 truncate">{s.label}</p>
                  <p className="text-[10px] text-slate-500">{i18n.t("misc.occurrences", { ns: "classement", count: s.count })}</p>
                </div>
                <Button 
                  aria-label={t("suggestionsPanel.creerUnMarchandAPartir")}
                  size="sm" 
                  variant="ghost" 
                  className="h-10 w-10 md:h-7 md:w-7 p-0 text-amber-600 hover:text-amber-700 hover:bg-amber-100"
                  onClick={() => {
                    setNewName(s.label)
                    setNewAliases(s.label)
                    setNewOpen(true)
                  }}
                >
                  <PlusCircle className="h-4 w-4" />
                </Button>
              </div>
            ))}
            {suggestions.length === 0 && (
              <p className="text-xs text-slate-400 text-center py-4 italic">{t("suggestionsPanel.toutEstNormalise")}</p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
