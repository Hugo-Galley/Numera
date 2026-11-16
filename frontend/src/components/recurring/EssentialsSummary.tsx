import { useTranslation } from "react-i18next"
import { ShieldCheck } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import { ResteAVivreCard } from "./ResteAVivreCard"

interface CostTotals { monthly: number; annual: number }

/** Abonnements essentiels / non essentiels (totaux du backend) et reste à vivre. */
export function EssentialsSummary({ totals, refreshKey }: { totals?: Record<string, CostTotals>; refreshKey?: unknown }) {
  const { t } = useTranslation("recurring")
  const rows = [
    { key: "essential", label: t("essentials.essentials"), color: "text-slate-900" },
    { key: "non_essential", label: t("essentials.nonEssentials"), color: "text-amber-700" },
  ]
  return (
    <div className="grid gap-3 md:gap-6 md:grid-cols-2">
      <Card className="shadow-xs border-slate-100">
        <CardHeader className="pb-2">
          <CardDescription className="flex items-center gap-2 font-medium text-slate-500">
            <ShieldCheck className="h-4 w-4" /> {t("essentials.split")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {rows.map(({ key, label, color }) => (
            <div key={key} className="flex items-baseline justify-between gap-3">
              <span className="text-sm font-medium text-slate-600">{label}</span>
              <span className="text-right tabular-nums">
                <span className={`text-lg font-black ${color}`}>
                  {t("essentials.perMonth", { amount: formatCurrency(totals?.[key]?.monthly ?? 0) })}
                </span>
                <span className="ml-2 text-xs text-slate-400">
                  {t("essentials.perYear", { amount: formatCurrency(totals?.[key]?.annual ?? 0) })}
                </span>
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
      <ResteAVivreCard refreshKey={refreshKey} />
    </div>
  )
}
