import { useTranslation } from "react-i18next"
import { useEffect, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Filter, Hash, ShoppingBag, Tag } from "lucide-react"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CategoriesTab } from "@/components/classement/CategoriesTab"
import { MerchantsTab } from "@/components/classement/MerchantsTab"
import { RulesTab } from "@/components/classement/RulesTab"
import { TagsTab } from "@/components/classement/TagsTab"
import { TransferRulesSection } from "@/components/classement/TransferRulesSection"

const TABS = [
  { value: "categories", icon: Tag },
  { value: "tags", icon: Hash },
  { value: "merchants", icon: ShoppingBag },
  { value: "rules", icon: Filter },
] as const

type TabValue = (typeof TABS)[number]["value"]

function resolveTab(tab: string | null): TabValue {
  return TABS.some((t) => t.value === tab) ? (tab as TabValue) : "categories"
}

// Tout ce qui sert à ranger les transactions : catégories, tags, marchands et règles automatiques
export default function Classement() {
  const { t } = useTranslation("classement")
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = searchParams.get("tab")
  const [activeTab, setActiveTab] = useState<TabValue>(resolveTab(requested))
  const tabsListRef = useRef<HTMLDivElement>(null)

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

  const changeTab = (value: string) => {
    setActiveTab(value as TabValue)
    setSearchParams({ tab: value }, { replace: true })
  }

  return (
    <div className="space-y-6 pb-10 md:space-y-8">
      <div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900">{t("classement.classement")}</h1>
        <p className="text-slate-500 mt-1">{t("classement.categoriesTagsMarchandsEtRegles")}</p>
      </div>

      <Tabs value={activeTab} onValueChange={changeTab} className="w-full">
        <div className="-mx-4 px-4 md:mx-0 md:px-0">
          <TabsList ref={tabsListRef} className="scroll-fade-x bg-slate-100 p-1 rounded-xl mb-4 sm:mb-6 flex h-12 w-full justify-start gap-1 sm:inline-flex sm:h-10 sm:w-auto [ms-overflow-style:none] scrollbar-none [&::-webkit-scrollbar]:hidden">
            {TABS.map(({ value, icon: Icon }) => (
              <TabsTrigger key={value} value={value} className="h-10 shrink-0 rounded-lg px-2.5 sm:h-auto sm:px-6">
                <Icon className="hidden h-4 w-4 mr-2 sm:inline" /> {t(`classement.tabs.${value}`)}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <TabsContent value="categories">
          <CategoriesTab />
        </TabsContent>
        <TabsContent value="tags">
          <TagsTab />
        </TabsContent>
        <TabsContent value="merchants">
          <MerchantsTab />
        </TabsContent>
        <TabsContent value="rules" className="space-y-10">
          <RulesTab />
          <div className="border-t border-slate-100 pt-8">
            <TransferRulesSection />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
