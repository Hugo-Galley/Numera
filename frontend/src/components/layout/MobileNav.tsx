import { useState } from "react"
import { NavLink, useLocation } from "react-router-dom"
import { LayoutDashboard, ClipboardCheck, Wallet, TrendingUp, Menu } from "lucide-react"
import { cn } from "@/lib/utils"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Sidebar } from "./Sidebar"

// Les 4 destinations les plus consultées ; tout le reste est dans « Plus » (même menu que le bureau).
const tabs = [
  { name: "Accueil", href: "/", icon: LayoutDashboard, end: true },
  { name: "Mois", href: "/month", icon: ClipboardCheck, end: false },
  { name: "Comptes", href: "/accounts", icon: Wallet, end: false },
  { name: "Placements", href: "/investments", icon: TrendingUp, end: false },
]

/** Barre d'onglets fixe en bas de l'écran, visible uniquement sous le breakpoint `md`. */
export function MobileNav() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const inTabs = tabs.some((t) => (t.end ? pathname === t.href : pathname.startsWith(t.href)))

  return (
    <>
      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex border-t bg-white/95 backdrop-blur md:hidden pb-[env(safe-area-inset-bottom)]"
        aria-label="Navigation principale"
      >
        {tabs.map((tab) => (
          <NavLink
            key={tab.href}
            to={tab.href}
            end={tab.end}
            className={({ isActive }) =>
              cn(
                "flex min-h-[56px] flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium",
                isActive ? "text-slate-900" : "text-slate-500"
              )
            }
          >
            <tab.icon className="h-5 w-5" aria-hidden="true" />
            {tab.name}
          </NavLink>
        ))}
        <button
          type="button"
          onClick={() => setOpen(true)}
          className={cn(
            "flex min-h-[56px] flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium",
            !inTabs ? "text-slate-900" : "text-slate-500"
          )}
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
          Plus
        </button>
      </nav>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="bottom" className="max-h-[85dvh] rounded-t-2xl p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation</SheetTitle>
            <SheetDescription>Toutes les pages de Numera</SheetDescription>
          </SheetHeader>
          <Sidebar className="border-none" hideBrand onItemClick={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
    </>
  )
}
