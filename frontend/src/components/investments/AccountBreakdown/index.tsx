import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/layout/ErrorState"
import { PortfolioBreakdown } from "@/components/investments/PortfolioBreakdown"
import { getAnalyticsDiversityScanner } from "@/lib/api/analytics"
import type { ApiResponse } from "@/lib/api/types"
import { resetApiCache } from "@/lib/apiCache"

type Scanner = ApiResponse<"/analytics/diversity-scanner", "get">

interface AccountBreakdownProps {
  accountId: number
  /** Change à chaque rechargement des données du compte : relance le calcul */
  reloadKey?: unknown
}

/** Répartition d'un compte d'investissement : charge `/analytics/diversity-scanner?account_id=` et affiche le donut. */
export function AccountBreakdown({ accountId, reloadKey }: AccountBreakdownProps) {
  const { t } = useTranslation("investments")
  const [data, setData] = useState<Scanner | null>(null)
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading")
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setStatus("loading")
    getAnalyticsDiversityScanner(`?account_id=${accountId}`)
      .then((res) => {
        if (cancelled) return
        setData(res)
        setStatus("ready")
      })
      .catch(() => !cancelled && setStatus("error"))
    return () => {
      cancelled = true
    }
  }, [accountId, reloadKey, attempt])

  if (status === "loading" && !data) return <Skeleton className="h-72 w-full rounded-xl" />
  if (status === "error") {
    return <ErrorState message={t("breakdown.loadFailed")} onRetry={() => { resetApiCache(); setAttempt((n) => n + 1) }} />
  }
  if (!data) return null
  return <PortfolioBreakdown data={data} scope="account" />
}
