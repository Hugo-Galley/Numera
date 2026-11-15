import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Users } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getAnalyticsPortfolio } from "@/lib/api/analytics"
import type { ApiResponse } from "@/lib/api/types"
import { formatCurrency, formatRate } from "@/lib/utils"

type ThirdPartyAccount = NonNullable<ApiResponse<"/analytics/portfolio", "get">["third_party_accounts"]>[number]

const signed = (value: number) => `${value >= 0 ? "+" : ""}${formatCurrency(value)}`

/** Comptes titres détenus pour un tiers : affichés à part, jamais comptés dans les totaux de la page. */
export function ThirdPartyAccounts() {
  const { t } = useTranslation("investments")
  const [accounts, setAccounts] = useState<ThirdPartyAccount[]>([])

  useEffect(() => {
    let cancelled = false
    getAnalyticsPortfolio()
      .then((overview) => { if (!cancelled) setAccounts(overview.third_party_accounts ?? []) })
      .catch(() => { /* section facultative : la page reste utilisable sans elle */ })
    return () => { cancelled = true }
  }, [])

  if (accounts.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Users className="h-5 w-5 text-amber-600" />
          {t("thirdParty.title")}
        </CardTitle>
        <CardDescription>{t("thirdParty.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {accounts.map((account) => (
          <Link
            key={account.account_id}
            to={`/accounts/${account.account_id}`}
            className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 rounded-lg border border-slate-200 p-3 hover:bg-slate-50"
          >
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-900">{account.account_name}</span>
              {account.held_for && (
                <Badge variant="secondary" className="bg-amber-50 font-semibold text-amber-700 border-amber-200">
                  {t("thirdParty.heldFor", { name: account.held_for })}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-6 text-right">
              <div>
                <p className="text-xs text-slate-500">{t("thirdParty.value")}</p>
                <p className="font-semibold tabular-nums">{formatCurrency(account.value_eur)}</p>
              </div>
              {account.unrealized_eur != null && (
                <div>
                  <p className="text-xs text-slate-500">{t("thirdParty.unrealized")}</p>
                  <p className={`font-semibold tabular-nums ${account.unrealized_eur >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                    {signed(account.unrealized_eur)}
                    {account.unrealized_pct != null && <span className="ml-1 text-xs amount-blur">({formatRate(account.unrealized_pct, 1)})</span>}
                  </p>
                </div>
              )}
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  )
}
