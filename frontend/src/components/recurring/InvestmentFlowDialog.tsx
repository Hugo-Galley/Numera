import i18n from "i18next"
import { accountTypeLabel } from "@/lib/labels"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { ArrowRight, CalendarClock, ChevronRight, Repeat } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { formatCurrency, frequencyLabel } from "@/lib/utils"

export interface FlowAccount {
  id: number
  name: string
  currency: string
  type: string
  institution?: string | null
  logo?: string | null
}

export interface FlowRecurring {
  name: string
  amount: number
  currency: string
  frequency: string
  day_of_month: number | null
  account_id: number
  transfer_to_account_id?: number | null
  ticker?: string | null
  isin?: string | null
  /** Nom lisible du titre (ex. « MSCI World »), résolu par le backend */
  security_name?: string | null
  quantity?: number | null
  logo?: string | null
}

interface Props {
  recurring: FlowRecurring | null
  accounts: FlowAccount[]
  nextOccurrence?: string | null
  /** « subscription » : l'argent part du compte vers un bénéficiaire (marchand), sans titre acheté */
  variant?: "investment" | "subscription"
  onClose: () => void
}

function Node({ title, subtitle, logo, name, ticker, isin, tone }: {
  title: string
  subtitle: string
  logo?: string | null
  name: string
  ticker?: string | null
  isin?: string | null
  tone: "rose" | "indigo" | "emerald"
}) {
  const ring = {
    rose: "ring-rose-200 bg-rose-50",
    indigo: "ring-indigo-200 bg-indigo-50",
    emerald: "ring-emerald-200 bg-emerald-50",
  }[tone]
  return (
    <div className="flex w-28 shrink-0 flex-col items-center gap-2 text-center md:w-32">
      <div className={`flex h-16 w-16 items-center justify-center rounded-2xl ring-4 md:h-20 md:w-20 ${ring}`}>
        <CompanyLogo logo={logo} name={name} ticker={ticker ?? undefined} isin={isin ?? undefined} className="h-10 w-10 rounded-xl md:h-12 md:w-12" />
      </div>
      <div className="min-w-0">
        <p className="wrap-break-word text-sm font-black leading-tight text-slate-900">{title}</p>
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{subtitle}</p>
      </div>
    </div>
  )
}

function Link({ label }: { label?: string }) {
  return (
    <div className="flex h-16 min-w-8 flex-1 flex-col items-center justify-center gap-1 md:h-20">
      {label && <span className="whitespace-nowrap text-[10px] font-black text-indigo-600 amount-blur">{label}</span>}
      <div className="relative flex w-full items-center">
        <div className="h-0.5 w-full border-t-2 border-dashed border-indigo-300" />
        <ChevronRight className="absolute -right-1 h-4 w-4 text-indigo-500" />
      </div>
    </div>
  )
}

export function InvestmentFlowDialog({ recurring, accounts, nextOccurrence, variant = "investment", onClose }: Props) {
  const isSub = variant === "subscription"
  const { t } = useTranslation("recurring")
  const source = recurring ? accounts.find((a) => a.id === recurring.account_id) : undefined
  const destId = recurring?.transfer_to_account_id
  const dest = destId ? accounts.find((a) => a.id === destId) : undefined
  const hasSecurity = !!recurring && !!(recurring.ticker || recurring.isin)
  // Versement saisi directement depuis le compte investissement : pas de compte de départ connu
  const startsOnInvestment = source?.type === "investissement" && !dest

  const accountNode = (acc: FlowAccount | undefined, tone: "rose" | "indigo") => (
    <Node
      title={acc?.name ?? "Compte inconnu"}
      subtitle={acc ? accountTypeLabel(acc.type) ?? acc.type : ""}
      logo={acc?.logo}
      name={acc?.institution || acc?.name || "?"}
      tone={tone}
    />
  )

  return (
    <Dialog open={!!recurring} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        {recurring && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-xl font-black">
                <CompanyLogo logo={recurring.logo} name={recurring.name} ticker={recurring.ticker ?? undefined} className="h-8 w-8 rounded-lg" />
                {recurring.name}
              </DialogTitle>
              <DialogDescription>{t(isSub ? "investmentFlowDialog.parcoursDeLArgentSubscription" : "investmentFlowDialog.parcoursDeLArgentInvesti")}</DialogDescription>
            </DialogHeader>

            <div className="rounded-2xl border border-indigo-100 bg-linear-to-br from-indigo-50/60 to-white p-4 md:p-6">
              <div className="mb-6 text-center">
                <p className="text-3xl font-black tabular-nums text-slate-900">
                  {formatCurrency(recurring.amount, recurring.currency)}
                </p>
                <p className="mt-1 flex items-center justify-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                  <Repeat className="h-3.5 w-3.5" />
                  {frequencyLabel(recurring.frequency)}
                  {recurring.day_of_month ? i18n.t("misc.onDay", { ns: "recurring", day: recurring.day_of_month }) : ""}
                </p>
              </div>

              <div className="flex items-start justify-center gap-1 overflow-x-auto px-2 pb-1 pt-2">
                {!startsOnInvestment && accountNode(source, "rose")}
                {!startsOnInvestment && <Link label={formatCurrency(recurring.amount, recurring.currency)} />}
                {isSub ? (
                  <Node title={recurring.name} subtitle={t("investmentFlowDialog.beneficiary")} logo={recurring.logo} name={recurring.name} tone="emerald" />
                ) : (
                  accountNode(dest ?? (startsOnInvestment ? source : undefined), "indigo")
                )}
                {hasSecurity && !isSub && (
                  <>
                    <Link label={recurring.quantity ? `${recurring.quantity} part(s)` : t("investmentFlowDialog.achat")} />
                    <Node
                      title={recurring.security_name || recurring.name}
                      subtitle={recurring.ticker || recurring.isin || i18n.t("misc.boughtSecurity", { ns: "recurring" })}
                      logo={recurring.logo}
                      name={recurring.name}
                      ticker={recurring.ticker}
                      isin={recurring.isin}
                      tone="emerald"
                    />
                  </>
                )}
              </div>
            </div>

            {nextOccurrence && (
              <p className="flex items-center justify-center gap-2 text-sm text-slate-500">
                <CalendarClock className="h-4 w-4" />
                {t("investmentFlowDialog.prochainPassage")} <span className="font-bold text-slate-800">{new Date(nextOccurrence).toLocaleDateString(appLocale(), { day: "numeric", month: "long" })}</span>
                <ArrowRight className="h-3.5 w-3.5 text-slate-300" />
              </p>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
