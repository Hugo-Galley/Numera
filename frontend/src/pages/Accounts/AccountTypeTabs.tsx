import { Landmark, LayoutGrid, PiggyBank, TrendingUp, Wallet } from "lucide-react"
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { Account } from "./types"

export type AccountGroup = "all" | "courant" | "epargne" | "investissement" | "credit"

/** Onglet d'un compte : l'assurance vie est rangée avec l'investissement. */
export function accountGroup(type: string): Exclude<AccountGroup, "all"> {
  if (type === "investissement" || type === "assurance_vie") return "investissement"
  if (type === "epargne" || type === "credit") return type
  return "courant"
}

const GROUPS: { value: AccountGroup; icon: ReactNode }[] = [
  { value: "all", icon: <LayoutGrid className="h-4 w-4" /> },
  { value: "courant", icon: <Wallet className="h-4 w-4" /> },
  { value: "epargne", icon: <PiggyBank className="h-4 w-4" /> },
  { value: "investissement", icon: <TrendingUp className="h-4 w-4" /> },
  { value: "credit", icon: <Landmark className="h-4 w-4" /> },
]

/** Onglets de filtre par type (même présentation que la page Récurrences) ; un type sans compte n'a pas d'onglet. */
export function AccountTypeTabs({ accounts, value, onChange }: { accounts: Account[]; value: AccountGroup; onChange: (v: AccountGroup) => void }) {
  const { t } = useTranslation("accounts")
  const counts = new Map<AccountGroup, number>([["all", accounts.length]])
  for (const a of accounts) {
    const g = accountGroup(a.type)
    counts.set(g, (counts.get(g) ?? 0) + 1)
  }
  const shown = GROUPS.filter((g) => g.value === "all" || (counts.get(g.value) ?? 0) > 0)
  if (shown.length <= 2) return null
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as AccountGroup)}>
      <div className="scroll-fade-x -mx-4 overflow-x-auto px-4 md:mx-0 md:overflow-visible md:px-0 scrollbar-none [&::-webkit-scrollbar]:hidden">
        <TabsList className="bg-slate-100 p-1 w-max min-w-full md:w-auto md:min-w-0 h-11 md:h-auto">
          {shown.map((g) => (
            <TabsTrigger key={g.value} value={g.value} className="rounded-lg gap-2">
              {g.icon}
              {t(`tabs.${g.value}`)}
              <span className="text-xs tabular-nums text-muted-foreground">{counts.get(g.value) ?? 0}</span>
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
    </Tabs>
  )
}
