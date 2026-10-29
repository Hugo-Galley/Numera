import { ArrowLeftRight, Bell, Calculator, CalendarDays, ClipboardCheck, Gift, HandCoins, Landmark, LayoutDashboard, PiggyBank, Repeat, Settings, ShieldCheck, Sparkles, Tags, TrendingUp, Wallet } from "lucide-react"

// Mêmes destinations que la barre latérale, plus des raccourcis vers les onglets (⌘K « calendrier »…)
export const NAVIGATION = [
  { name: "Tableau de bord", href: "/", icon: LayoutDashboard },
  { name: "Bilan du mois", href: "/month/bilan", icon: Sparkles },
  { name: "Revue de mois", href: "/month/revue", icon: ClipboardCheck },
  { name: "Comparaison mensuelle", href: "/month/comparaison", icon: ArrowLeftRight },
  { name: "Bilan annuel", href: "/wrapped", icon: Gift },
  { name: "Centre d'actions", href: "/audit", icon: ShieldCheck },
  { name: "Comptes", href: "/accounts", icon: Wallet },
  { name: "Épargne", href: "/savings", icon: PiggyBank },
  { name: "Investissements", href: "/investments", icon: TrendingUp },
  { name: "Fiscalité", href: "/tax", icon: Landmark },
  { name: "Échéances (récurrences)", href: "/recurring", icon: Repeat },
  { name: "Calendrier", href: "/recurring?tab=calendar", icon: CalendarDays },
  { name: "Salaire et aides (CAF, prime d'activité, APL)", href: "/recurring?tab=salary", icon: Wallet },
  { name: "Remboursements", href: "/reimbursements", icon: HandCoins },
  { name: "Simulateur", href: "/tools", icon: Calculator },
  { name: "Classement : catégories", href: "/classement?tab=categories", icon: Tags },
  { name: "Classement : tags", href: "/classement?tab=tags", icon: Tags },
  { name: "Classement : marchands", href: "/classement?tab=merchants", icon: Tags },
  { name: "Classement : règles (catégorisation, virements)", href: "/classement?tab=rules", icon: Tags },
  { name: "Virements internes (suggestions, liés)", href: "/audit?vue=virements", icon: ArrowLeftRight },
  { name: "Notifications (ntfy, Telegram)", href: "/settings?tab=notifications", icon: Bell },
  { name: "Paramètres", href: "/settings", icon: Settings },
]
