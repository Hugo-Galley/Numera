import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Scissors, Wallet } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { getAnalyticsResteAVivre } from "@/lib/api/analytics"
import type { ApiResponse } from "@/lib/api/types"
import { safeStorage } from "@/lib/storage"
import { formatCurrency } from "@/lib/utils"

type ResteAVivre = ApiResponse<"/analytics/reste-a-vivre", "get">
type Mode = "essential" | "all"
const STORAGE_KEY = "reste-a-vivre-mode"

function storedMode(): Mode {
  try { return safeStorage.getItem(STORAGE_KEY) === "all" ? "all" : "essential" } catch { return "essential" }
}

/** Reste à vivre mensuel (calculé par le backend) ; `refreshKey` recharge après un changement de classement. */
export function ResteAVivreCard({ refreshKey }: { refreshKey?: unknown }) {
  const { t } = useTranslation("recurring")
  const [data, setData] = useState<ResteAVivre | null>(null)
  const [mode, setMode] = useState<Mode>(storedMode)

  useEffect(() => {
    let alive = true
    getAnalyticsResteAVivre().then((d) => { if (alive) setData(d) }).catch(() => { if (alive) setData(null) })
    return () => { alive = false }
  }, [refreshKey])

  const changeMode = (next: Mode) => {
    setMode(next)
    try { safeStorage.setItem(STORAGE_KEY, next) } catch { /* stockage indisponible */ }
  }

  const amount = data ? (mode === "essential" ? data.reste_a_vivre_essentiel : data.reste_a_vivre_total) : 0
  const deducted = data ? (mode === "essential" ? data.charges_essentielles : data.charges_essentielles + data.charges_non_essentielles) : 0
  return (
    <Card className="shadow-xs border-slate-100">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardDescription className="flex items-center gap-2 font-medium text-slate-500">
            <Wallet className="h-4 w-4" /> {t("essentials.resteAVivre")}
          </CardDescription>
          <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-0.5" role="group" aria-label={t("essentials.modeLabel")}>
            {(["essential", "all"] as const).map((m) => (
              <Button
                key={m}
                size="sm"
                variant={mode === m ? "white" : "ghost"}
                aria-pressed={mode === m}
                className={`h-7 rounded-md px-2 text-[11px] font-bold ${mode === m ? "shadow-xs" : "text-slate-500"}`}
                onClick={() => changeMode(m)}
              >
                {m === "essential" ? t("essentials.modeEssential") : t("essentials.modeAll")}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {!data ? <Skeleton className="h-9 w-40" /> : (
          <>
            <CardTitle className={`text-2xl md:text-3xl font-black ${amount >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              {formatCurrency(amount)}
            </CardTitle>
            <p className="text-xs text-slate-400">
              {t("essentials.formula", { income: formatCurrency(data.revenus_recurrents), charges: formatCurrency(deducted) })}
            </p>
            <p className="flex items-center gap-1.5 text-xs font-semibold text-amber-700">
              <Scissors className="h-3.5 w-3.5" />
              {t("essentials.couldCut", { amount: formatCurrency(data.charges_non_essentielles) })}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
