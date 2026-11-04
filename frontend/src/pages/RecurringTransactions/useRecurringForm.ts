import { format } from "date-fns"
import { useEffect, useState } from "react"
import type { useRecurringState } from "./useRecurringState"

/** Formulaire de récurrence et vue des abonnements (dérivés de l'onglet secondaire). */
export function useRecurringForm(p: ReturnType<typeof useRecurringState>) {
  const { accounts, subsData, activeTab, subTab } = p
  // Form State
  const [formData, setFormData] = useState({
    account_id: "",
    name: "",
    type: "Sortie",
    amount: "",
    currency: "EUR",
    category_id: "none",
    frequency: "monthly",
    day_of_month: "1",
    excluded_months: [] as number[],
    start_date: format(new Date(), "yyyy-MM-dd"),
    is_active: true,
    auto_generate: false,
    transfer_to_account_id: "none",
    transfer_credit_day: "",
    note: "",
    asset_class: "",
    sector: "",
    geographic_zone: "",
    ticker: "",
    isin: "",
    quantity: "",
    unit_price: "",
    whole_shares: false,
    etf_profile_id: null as number | null,
    logo: null as string | null,
  })

  const selectedAccount = accounts.find(a => a.id.toString() === formData.account_id)
  // Virement vers un compte investissement : la sortie et le dépôt + achat de parts sont créés ensemble
  const transferDest = accounts.find(a => a.id.toString() === formData.transfer_to_account_id)
  const transferToInvestment = formData.type === "Sortie" && selectedAccount?.type !== "investissement" && transferDest?.type === "investissement"
  const isInvestment = selectedAccount?.type === "investissement" || (!!formData.ticker && !transferToInvestment)
  const showSecurities = isInvestment || transferToInvestment

  // Changer de compte ne doit pas laisser un type de l'autre famille (une « Entrée » sur un PEA)
  // (seul le type du compte décide : un titre saisi depuis un compte courant garde Sortie pour le virement)
  const accountIsInvestment = selectedAccount?.type === "investissement"
  useEffect(() => {
    // Mobile : garde l'onglet actif visible dans la liste d'onglets scrollable
    document.querySelector<HTMLElement>('[role="tab"][data-state="active"]')?.scrollIntoView({ inline: "center", block: "nearest" })
  }, [activeTab])

  useEffect(() => {
    const investmentTypes = ["versement", "retrait", "dividende"]
    if (accountIsInvestment && !investmentTypes.includes(formData.type)) {
      setFormData(prev => ({ ...prev, type: "versement" }))
    } else if (selectedAccount && !accountIsInvestment && !formData.ticker && investmentTypes.includes(formData.type)) {
      setFormData(prev => ({ ...prev, type: "Sortie" }))
    }
  }, [selectedAccount, accountIsInvestment, formData.type, formData.ticker])

  const allSubs = subsData?.subscriptions || []
  // Onglet (`kind`), totaux et appartenance au total : calculés par le backend
  const activeSubs = allSubs.filter((s: any) => s.is_recurring_entity && s.kind === subTab)
  const potentialSubs = allSubs.filter((s: any) => !s.is_recurring_entity && s.kind === subTab)
  const countedSubs = activeSubs.filter((s: any) => s.in_kind_total)
  const monthlyTotal: number = subsData?.totals_by_kind?.[subTab]?.monthly ?? 0
  const annualTotal: number = subsData?.totals_by_kind?.[subTab]?.annual ?? 0
  const monthlyBreakdown = [...countedSubs].sort((a: any, b: any) => b.monthly_cost - a.monthly_cost)
  return { formData, setFormData, selectedAccount, transferDest, transferToInvestment, isInvestment, showSecurities, accountIsInvestment, allSubs, activeSubs, potentialSubs, countedSubs, monthlyTotal, annualTotal, monthlyBreakdown }
}
