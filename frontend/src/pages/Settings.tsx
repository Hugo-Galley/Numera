import { useEffect, useRef, useState } from "react"
import { Navigate, useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Bell, Database, ShieldCheck, SlidersHorizontal } from "lucide-react"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BackupCard } from "@/components/settings/BackupCard"
import { BudgetPeriodCard } from "@/components/settings/BudgetPeriodCard"
import { DangerZoneCard } from "@/components/settings/DangerZoneCard"
import { DisplayCard } from "@/components/settings/DisplayCard"
import { ExportCard } from "@/components/settings/ExportCard"
import { ImportHistoryCard } from "@/components/settings/ImportHistoryCard"
import { LoginActivityCard } from "@/components/settings/LoginActivityCard"
import { McpAccessCard } from "@/components/settings/McpAccessCard"
import { NotificationsTab } from "@/components/settings/NotificationsTab"
import { PasskeyCard } from "@/components/settings/PasskeyCard"
import { PasswordCard, ProfileInfoCard } from "@/components/settings/ProfileForm"
import { TotpCard } from "@/components/settings/TotpCard"

const TABS = [
  { value: "general", icon: SlidersHorizontal },
  { value: "notifications", icon: Bell },
  { value: "security", icon: ShieldCheck },
  { value: "data", icon: Database },
] as const

type TabValue = (typeof TABS)[number]["value"]

// Anciens onglets (?tab=) : ceux restés dans les Paramètres changent de nom, les autres ont quitté la page
const LEGACY_TABS: Record<string, TabValue> = { account: "security", system: "data" }
const MOVED_TABS: Record<string, string> = {
  categories: "/classement?tab=categories",
  tags: "/classement?tab=tags",
  merchants: "/classement?tab=merchants",
  rules: "/classement?tab=rules",
  transferts: "/audit?vue=virements",
  transfers: "/audit?vue=virements",
  import: "/accounts?import=1",
}

function resolveTab(tab: string | null): TabValue {
  if (!tab) return "general"
  if (tab in LEGACY_TABS) return LEGACY_TABS[tab]
  return TABS.some((t) => t.value === tab) ? (tab as TabValue) : "general"
}

export default function Settings() {
  const { t } = useTranslation("settings")
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = searchParams.get("tab")
  const [activeTab, setActiveTab] = useState<TabValue>(resolveTab(requested))
  const tabsListRef = useRef<HTMLDivElement>(null)

  // Lien interne vers un autre onglet alors que la page est déjà ouverte (Omnibox, menu) : suivre ?tab=
  useEffect(() => {
    if (requested) setActiveTab(resolveTab(requested))
  }, [requested])

  // Garde l'onglet actif visible dans la liste défilante (mobile)
  useEffect(() => {
    const list = tabsListRef.current
    const el = list?.querySelector<HTMLElement>('[data-state="active"]')
    if (!list || !el) return
    const raf = requestAnimationFrame(() => {
      list.scrollTo({ left: el.offsetLeft - (list.clientWidth - el.offsetWidth) / 2, behavior: "smooth" })
    })
    return () => cancelAnimationFrame(raf)
  }, [activeTab])

  if (requested && requested in MOVED_TABS) return <Navigate to={MOVED_TABS[requested]} replace />

  const changeTab = (value: string) => {
    setActiveTab(value as TabValue)
    setSearchParams({ tab: value }, { replace: true })
  }

  return (
    <div className="space-y-6 pb-10 md:space-y-8 [&_input]:text-base md:[&_input]:text-sm">
      <div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900">{t("title")}</h1>
        <p className="text-slate-500 mt-1">{t("subtitle")}</p>
      </div>

      <Tabs value={activeTab} onValueChange={changeTab} className="w-full">
        <div className="-mx-4 px-4 md:mx-0 md:px-0">
          <TabsList ref={tabsListRef} className="scroll-fade-x bg-slate-100 p-1 rounded-xl mb-4 sm:mb-6 flex h-12 w-full justify-start gap-1 sm:inline-flex sm:h-10 sm:w-auto [ms-overflow-style:none] scrollbar-none [&::-webkit-scrollbar]:hidden">
            {TABS.map(({ value, icon: Icon }) => (
              <TabsTrigger key={value} value={value} className="h-10 shrink-0 rounded-lg px-2.5 sm:h-auto sm:px-6">
                <Icon className="hidden h-4 w-4 mr-2 sm:inline" /> {t(`tabs.${value}.label`)}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {TABS.map(({ value }) => (
          <TabsContent key={value} value={value} className="space-y-6">
            {value !== "notifications" && <p className="text-sm text-slate-500">{t(`tabs.${value}.intro`)}</p>}
            {value === "general" && (
              <>
                <ProfileInfoCard />
                <DisplayCard />
                <BudgetPeriodCard />
              </>
            )}
            {value === "notifications" && <NotificationsTab />}
            {value === "security" && (
              <>
                <PasswordCard />
                <PasskeyCard />
                <TotpCard />
                <McpAccessCard />
                <LoginActivityCard />
              </>
            )}
            {value === "data" && (
              <>
                <BackupCard />
                <ExportCard />
                <ImportHistoryCard />
                <DangerZoneCard />
              </>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
