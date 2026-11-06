import i18n from "i18next"
import { ArrowLeftRight, Bell, Calculator, CalendarDays, ClipboardCheck, Gift, HandCoins, Landmark, LayoutDashboard, PiggyBank, Repeat, Settings, ShieldCheck, Sparkles, Tags, TrendingUp, Wallet } from "lucide-react"

// Mêmes destinations que la barre latérale, plus des raccourcis vers les onglets (⌘K « calendrier »…)
export const NAVIGATION = [
  { key: "dashboard" as const, href: "/", icon: LayoutDashboard },
  { key: "monthReport" as const, href: "/month/bilan", icon: Sparkles },
  { key: "monthReview" as const, href: "/month/revue", icon: ClipboardCheck },
  { key: "monthComparison" as const, href: "/month/comparaison", icon: ArrowLeftRight },
  { key: "wrapped" as const, href: "/wrapped", icon: Gift },
  { key: "actions" as const, href: "/audit", icon: ShieldCheck },
  { key: "accounts" as const, href: "/accounts", icon: Wallet },
  { key: "savings" as const, href: "/savings", icon: PiggyBank },
  { key: "investments" as const, href: "/investments", icon: TrendingUp },
  { key: "tax" as const, href: "/tax", icon: Landmark },
  { key: "recurring" as const, href: "/recurring", icon: Repeat },
  { key: "calendar" as const, href: "/recurring?tab=calendar", icon: CalendarDays },
  { key: "salary" as const, href: "/recurring?tab=salary", icon: Wallet },
  { key: "reimbursements" as const, href: "/reimbursements", icon: HandCoins },
  { key: "simulator" as const, href: "/tools", icon: Calculator },
  { key: "categories" as const, href: "/classement?tab=categories", icon: Tags },
  { key: "tags" as const, href: "/classement?tab=tags", icon: Tags },
  { key: "merchants" as const, href: "/classement?tab=merchants", icon: Tags },
  { key: "rules" as const, href: "/classement?tab=rules", icon: Tags },
  { key: "transfers" as const, href: "/audit?vue=virements", icon: ArrowLeftRight },
  { key: "notifications" as const, href: "/settings?tab=notifications", icon: Bell },
  { key: "settings" as const, href: "/settings", icon: Settings },
]

/** Libellé d'une destination, dans la langue de l'interface (lu à l'appel : les recherches se font sur le texte affiché). */
export const navigationName = (item: (typeof NAVIGATION)[number]): string => i18n.t(`nav.${item.key}`, { ns: "omnibox" })
