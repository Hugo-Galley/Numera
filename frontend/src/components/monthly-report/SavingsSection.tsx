import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { MonthlyReportData } from "./types"

function Figure({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`amount-blur whitespace-nowrap text-xl font-black tabular-nums ${tone ?? "text-slate-900"}`}>{value}</div>
      {hint && <div className="amount-blur text-[11px] text-slate-400">{hint}</div>}
    </div>
  )
}

export function SavingsSection({ data }: { data: MonthlyReportData }) {
  const { t } = useTranslation("month")
  const flow = data.money_flow
  const hasExceptional = data.exceptional_expenses > 0
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-black text-slate-900">{t("savingsSection.misDeCote")}</h2>
      <Card>
        <CardContent className="grid grid-cols-2 gap-x-6 gap-y-5 p-5 sm:grid-cols-4">
          {flow && <Figure label={t("savingsSection.epargne")} value={formatCurrency(flow.savings.amount)} />}
          {flow && <Figure label={t("savingsSection.investi")} value={formatCurrency(flow.investments.amount)} />}
          <Figure
            label={t("savingsSection.tauxDEpargne")}
            value={formatRate(data.savings_rate, 1)}
            hint={hasExceptional
              ? i18n.t("misc.excludingExceptional", { ns: "month", pct: formatRate(data.savings_rate_excl_exceptional, 1) })
              : i18n.t("misc.shareUnspent", { ns: "month" })}
          />
          <Figure
            label={t("savingsSection.variationDuPatrimoine")}
            value={`${data.net_worth_change >= 0 ? "+" : "−"}${formatCurrency(Math.abs(data.net_worth_change))}`}
            tone={data.net_worth_change >= 0 ? "text-emerald-600" : "text-rose-600"}
          />
        </CardContent>
      </Card>
    </section>
  )
}
