import { useState } from "react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { monthName } from "@/i18n/locale"
import { AccountLogo } from "@/components/ui/AccountLogo"
import { CalendarClock, ChevronDown, SlidersHorizontal, Star } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

import type { DashboardAccount } from "./types"

interface DashboardHeaderProps {
  accounts: DashboardAccount[]
  selectedAccountId: string
  setSelectedAccountId: (v: string) => void
  month: number
  setMonth: (v: number) => void
  year: number
  setYear: (v: number) => void
  periodRange?: string | null
  /** Position dans la période quand elle est en cours (« J23/30 »), sinon `null`. */
  progress?: { day: number; total: number } | null
}

export function DashboardHeader({
  accounts,
  selectedAccountId,
  setSelectedAccountId,
  month,
  setMonth,
  year,
  setYear,
  periodRange,
  progress = null,
}: DashboardHeaderProps) {
  const { t } = useTranslation("dashboard")
  // Mobile : les filtres tiennent sur une ligne (résumé + bouton) et se déplient à la demande
  const [filtersOpen, setFiltersOpen] = useState(false)
  const mainAccount = accounts.find(a => a.is_main)
  const selectedAccount = accounts.find(a => String(a.id) === selectedAccountId)
  const accountLabel = selectedAccountId === "all" ? t("allAccounts") : selectedAccount?.name ?? t("allAccounts")

  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 md:gap-6">
      <div className="min-w-0">
        <h1 className="text-2xl md:text-4xl font-extrabold tracking-tight text-slate-900">{t("title")}</h1>
        <p className="hidden sm:block text-slate-500 mt-1">{t("subtitle")}</p>
        {(periodRange || progress) && (
          <div className="mt-1.5 md:mt-2 flex flex-wrap items-center gap-1.5">
            {progress && (
              <span
                className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-800"
                title={t("currentPeriodHint")}
              >
                <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
                {t("currentPeriod", { day: progress.day, total: progress.total })}
              </span>
            )}
            {periodRange && (
              <span className="inline-flex items-center whitespace-nowrap rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-xs font-medium text-slate-500">
                {t("payPeriod", { range: periodRange })}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Mobile : une seule ligne (compte · mois) qui déplie les filtres */}
      <button
        type="button"
        className="sm:hidden flex h-11 w-full items-center gap-2 rounded-xl border bg-white px-3 text-left text-sm font-medium text-slate-900 shadow-xs"
        aria-expanded={filtersOpen}
        aria-controls="dashboard-filters"
        aria-label={t("filters.show")}
        onClick={() => setFiltersOpen(open => !open)}
      >
        <SlidersHorizontal className="h-4 w-4 shrink-0 text-slate-500" aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate">
          {accountLabel} · {monthName(month)} {year}
        </span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-slate-500 transition-transform", filtersOpen && "rotate-180")} aria-hidden="true" />
      </button>

      <div
        id="dashboard-filters"
        className={cn(
          "grid-cols-[1fr_auto] gap-2 sm:flex sm:flex-wrap sm:items-center md:gap-3 bg-white p-2 rounded-xl border shadow-xs w-full sm:w-fit",
          filtersOpen ? "grid" : "hidden sm:flex"
        )}
      >
        <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
          <SelectTrigger className="col-span-2 w-full sm:w-[160px] md:w-[180px] border-slate-200 sm:border-none shadow-none focus:ring-0 font-medium h-11 md:h-10 text-base md:text-sm">
            <SelectValue placeholder={t("placeholders.account")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("allAccounts")}</SelectItem>
            {accounts.filter((acc) => acc.active).map((acc) => (
              <SelectItem key={acc.id} value={String(acc.id)}>
                <span className="flex items-center gap-2"><AccountLogo accountId={acc.id} className="h-5 w-5" />{acc.name}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Separator orientation="vertical" className="h-6 hidden md:block" />
        <Select value={String(month)} onValueChange={(v: string) => setMonth(Number(v))}>
          <SelectTrigger className="w-full sm:w-[120px] md:w-[130px] border-slate-200 sm:border-none shadow-none focus:ring-0 h-11 md:h-10 text-base md:text-sm">
            <SelectValue placeholder={t("placeholders.month")} />
          </SelectTrigger>
          <SelectContent>
            {Array.from({ length: 12 }, (_, i) => (
              <SelectItem key={i + 1} value={String(i + 1)}>{monthName(i + 1)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Separator orientation="vertical" className="h-6 hidden md:block" />
        <Select value={String(year)} onValueChange={(v: string) => setYear(Number(v))}>
          <SelectTrigger className="w-[96px] sm:w-[90px] md:w-[100px] border-slate-200 sm:border-none shadow-none focus:ring-0 h-11 md:h-10 text-base md:text-sm">
            <SelectValue placeholder={t("placeholders.year")} />
          </SelectTrigger>
          <SelectContent>
            {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i).map((y) => (
              <SelectItem key={y} value={String(y)}>{y}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {mainAccount && (
          <>
            <Separator orientation="vertical" className="h-6 hidden md:block" />
            {/* Raccourci vers le compte principal : libellé explicite (l'étoile seule ne disait rien) */}
            <Link
              to={`/accounts/${mainAccount.id}`}
              aria-label={t("mainAccount.open", { name: mainAccount.name })}
              title={t("mainAccount.open", { name: mainAccount.name })}
              className="col-span-2 flex items-center gap-2 px-3 h-11 md:h-10 text-slate-700 border border-slate-200 bg-white hover:bg-slate-50 hover:text-slate-900 rounded-lg transition-colors text-sm shadow-xs"
            >
              <Star className="h-4 w-4 shrink-0 fill-amber-400 text-amber-500" aria-hidden="true" />
              <span className="flex min-w-0 flex-col leading-tight">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{t("mainAccount.label")}</span>
                <span className="truncate font-medium max-w-[240px] sm:max-w-[120px] md:max-w-[150px]">{mainAccount.name}</span>
              </span>
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
