import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { yearOptions } from "@/lib/years"
import type { SavingsCtx } from "./useSavings"

/** En-tête : titre et sélecteurs de période. */
export function SavingsHeader({ ctx }: { ctx: SavingsCtx }) {
  const { t } = useTranslation("savings")
  const { month, months, period, setMonth, setPeriod, setYear, year } = ctx
  return (
    <>
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-slate-900">{t("savingsHeader.suiviDeLEpargne")}</h1>
          <p className="text-sm text-slate-500 mt-1 md:text-base">{t("savingsHeader.gerezVotreCapaciteDAccumulation")}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3 bg-white p-1.5 rounded-xl border shadow-sm">
          <Select value={period} onValueChange={(v: any) => setPeriod(v)}>
            <SelectTrigger className="w-full sm:w-[140px] border-none shadow-none focus:ring-0 font-medium">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="monthly">{t("savingsHeader.mensuel")}</SelectItem>
              <SelectItem value="all-time">{t("savingsHeader.toutLeTemps")}</SelectItem>
            </SelectContent>
          </Select>

          {period === "monthly" && (
            <>
              <Separator orientation="vertical" className="hidden sm:block h-6" />
              <Select value={month} onValueChange={setMonth}>
                <SelectTrigger className="flex-1 sm:w-[130px] border-none shadow-none focus:ring-0">
                  <SelectValue placeholder={t("savingsHeader.mois")} />
                </SelectTrigger>
                <SelectContent>
                  {months.map((m, i) => (
                    <SelectItem key={i + 1} value={String(i + 1)}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Separator orientation="vertical" className="hidden sm:block h-6" />
              <Select value={year} onValueChange={setYear}>
                <SelectTrigger className="flex-1 sm:w-[100px] border-none shadow-none focus:ring-0">
                  <SelectValue placeholder={t("savingsHeader.annee")} />
                </SelectTrigger>
                <SelectContent>
                  {yearOptions(year).map((y) => (
                    <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
        </div>
      </div>
    </>
  )
}
