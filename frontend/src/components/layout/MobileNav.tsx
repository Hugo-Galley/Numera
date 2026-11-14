import { useState } from "react"
import { NavLink, useLocation } from "react-router-dom"
import { LayoutDashboard, ClipboardCheck, Wallet, TrendingUp, Menu } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Sidebar } from "./Sidebar"

// Les 4 destinations les plus consultées ; tout le reste est dans « Plus » (même menu que le bureau).
const tabs = [
  { name: "home", href: "/", icon: LayoutDashboard, end: true },
  { name: "month", href: "/month", icon: ClipboardCheck, end: false },
  { name: "accounts", href: "/accounts", icon: Wallet, end: false },
  { name: "investments", href: "/investments", icon: TrendingUp, end: false },
] as const

/** Barre d'onglets fixe en bas de l'écran, visible uniquement sous le breakpoint `md`. */
export function MobileNav() {
  const { t } = useTranslation("nav")
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const inTabs = tabs.some((t) => (t.end ? pathname === t.href : pathname.startsWith(t.href)))

  return (
    <>
      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex border-t bg-white/95 backdrop-blur-sm md:hidden pb-[calc(env(safe-area-inset-bottom)*0.45)]"
        aria-label={t("mobile.label")}
      >
        {tabs.map((tab) => (
          <NavLink
            key={tab.href}
            to={tab.href}
            end={tab.end}
            className={({ isActive }) =>
              cn(
                "flex min-h-[52px] flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium",
                isActive ? "text-slate-900" : "text-slate-500"
              )
            }
          >
            <tab.icon className="h-5 w-5" aria-hidden="true" />
            {t(`mobile.${tab.name}`)}
          </NavLink>
        ))}
        <button
          type="button"
          onClick={() => setOpen(true)}
          className={cn(
            "flex min-h-[52px] flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium",
            !inTabs ? "text-slate-900" : "text-slate-500"
          )}
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
          {t("mobile.more")}
        </button>
      </nav>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="bottom" className="max-h-[85dvh] rounded-t-2xl p-0 pb-[env(safe-area-inset-bottom)]">
          <SheetHeader className="sr-only">
            <SheetTitle>{t("mobile.menuTitle")}</SheetTitle>
            <SheetDescription>{t("mobile.menuDescription")}</SheetDescription>
          </SheetHeader>
          <Sidebar className="border-none" hideBrand onItemClick={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
    </>
  )
}
