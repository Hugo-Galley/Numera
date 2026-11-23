import { useEffect, useRef, useState, type RefObject } from "react"
import { NavLink, useLocation } from "react-router-dom"
import {
  LayoutDashboard,
  Wallet,
  TrendingUp,
  Settings,
  CreditCard,
  PiggyBank,
  Eye,
  EyeOff,
  LogOut,
  Search,
  Repeat,
  HandCoins,
  ShieldCheck,
  Calculator,
  Landmark,
  Tags,
  ClipboardCheck,
  Gift,
  ChevronDown,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import { useUI } from "@/providers/UIProvider"
import { useAuth } from "@/providers/AuthProvider"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { getAnalyticsActions } from "@/lib/api/analytics"

// 12 entrées en 3 groupes toujours ouverts : Bilan, Revue et Comparaison sont des onglets de « Mois »,
// le calendrier et le salaire des onglets d'« Échéances ».
const navigationGroups = [
  {
    title: "overview",
    items: [
      { name: "dashboard", href: "/", icon: LayoutDashboard },
      { name: "month", href: "/month", icon: ClipboardCheck },
      { name: "wrapped", href: "/wrapped", icon: Gift },
      { name: "actions", href: "/audit", icon: ShieldCheck, badge: "actions" as const },
    ]
  },
  {
    title: "wealth",
    items: [
      { name: "accounts", href: "/accounts", icon: Wallet },
      { name: "savings", href: "/savings", icon: PiggyBank },
      { name: "investments", href: "/investments", icon: TrendingUp },
      { name: "tax", href: "/tax", icon: Landmark },
    ]
  },
  {
    title: "management",
    items: [
      { name: "recurring", href: "/recurring", icon: Repeat },
      { name: "reimbursements", href: "/reimbursements", icon: HandCoins },
      { name: "classement", href: "/classement", icon: Tags },
      { name: "simulator", href: "/tools", icon: Calculator },
    ]
  }
] as const

/** Nombre d'actions urgentes du Centre d'actions, relu au plus une fois par minute en naviguant. */
function useUrgentActionCount(): number {
  const { pathname } = useLocation()
  const [count, setCount] = useState(0)
  const lastFetch = useRef(0)

  useEffect(() => {
    if (Date.now() - lastFetch.current < 60_000) return
    lastFetch.current = Date.now()
    getAnalyticsActions<{ summary: { high_priority: number } }>()
      .then((data) => setCount(data.summary.high_priority))
      .catch(() => {})
  }, [pathname])

  return count
}

/** `true` tant qu'une partie de la liste est cachée sous le bas de la zone défilante (indice « il y a la suite »). */
function useMoreBelow(ref: RefObject<HTMLDivElement | null>): boolean {
  const [moreBelow, setMoreBelow] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => setMoreBelow(el.scrollTop + el.clientHeight < el.scrollHeight - 4)
    update()
    el.addEventListener("scroll", update, { passive: true })
    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => {
      el.removeEventListener("scroll", update)
      observer.disconnect()
    }
  }, [ref])
  return moreBelow
}

export function Sidebar({ className, onItemClick, hideBrand }: { className?: string, onItemClick?: () => void, hideBrand?: boolean }) {
  const { t } = useTranslation("nav")
  const { isPrivacyMode, togglePrivacyMode, setSearchOpen } = useUI()
  const { logout, username, profile } = useAuth()
  
  const urgentActions = useUrgentActionCount()
  const scrollRef = useRef<HTMLDivElement>(null)
  const moreBelow = useMoreBelow(scrollRef)

  const initials = username ? username.slice(0, 2).toUpperCase() : "?"
  const profilePicture = profile?.profile_picture_url

  return (
    <div className={cn("flex flex-col bg-white", className)}>
      {!hideBrand && (
        <div className="flex h-16 items-center border-b px-6">
          <CreditCard className="h-6 w-6 mr-2" />
          <span className="text-lg font-bold tracking-tight">Numera</span>
        </div>
      )}
      <div className="relative flex min-h-0 flex-1 flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto py-3">
        <nav className="space-y-3 px-3">
          {navigationGroups.map((group, i) => (
            <div key={i} className="space-y-1">
              <p className="px-3 pt-1 pb-1 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                {t(`groups.${group.title}`)}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    onClick={onItemClick}
                    className={({ isActive }) =>
                      cn(
                        // Page courante : fond, gras et barre à gauche (le fond seul se voyait mal dans le menu mobile)
                        "group relative flex items-center rounded-md px-3 text-sm font-medium transition-colors",
                        hideBrand ? "min-h-11" : "py-1.5",
                        isActive
                          ? "bg-slate-100 font-semibold text-slate-900 before:absolute before:inset-y-1.5 before:left-0 before:w-1 before:rounded-full before:bg-slate-900"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      )
                    }
                  >
                    <item.icon
                      className={cn(
                        "mr-3 h-5 w-5 shrink-0 transition-colors",
                        "group-hover:text-slate-900"
                      )}
                      aria-hidden="true"
                    />
                    {t(`items.${item.name}`)}
                    {"badge" in item && urgentActions > 0 && (
                      <span
                        className="ml-auto rounded-full bg-rose-600 px-2 py-0.5 text-[10px] font-bold text-white"
                        aria-label={t("urgentActions", { count: urgentActions })}
                      >
                        {urgentActions}
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </div>
      {moreBelow && (
        // Indice de défilement : la fin de la liste est cachée (écran bas, menu mobile)
        <button
          type="button"
          aria-label={t("moreBelow")}
          onClick={() => scrollRef.current?.scrollBy({ top: scrollRef.current.clientHeight * 0.8, behavior: "smooth" })}
          className="absolute inset-x-0 bottom-0 flex h-10 items-end justify-center bg-linear-to-t from-white via-white/90 to-transparent pb-1 text-slate-500 hover:text-slate-900"
        >
          <ChevronDown className="h-4 w-4 animate-bounce" aria-hidden="true" />
        </button>
      )}
      </div>
      {!hideBrand && (
      <div className="px-3 py-3 border-t flex gap-2">
        <Button 
          variant="outline" 
          size="sm" 
          className="flex-1 justify-start gap-2 text-slate-600 border-slate-200 px-3"
          onClick={togglePrivacyMode}
        >
          {isPrivacyMode ? (
            <>
              <Eye className="h-4 w-4" />
              <span className="truncate">{t("privacy.show")}</span>
            </>
          ) : (
            <>
              <EyeOff className="h-4 w-4" />
              <span className="truncate">{t("privacy.hide")}</span>
            </>
          )}
        </Button>
        <Button aria-label={t("search")}
          variant="outline"
          size="sm"
          className="px-3 text-slate-600 border-slate-200"
          onClick={() => setSearchOpen(true)}
        >
          <Search className="h-4 w-4" />
        </Button>
      </div>
      )}
      {hideBrand ? (
        // Menu mobile (feuille du bas) : un menu déroulant s'y superposerait à une 2e couche modale, on liste les actions à plat
        <div className="border-t p-3 pb-4 shrink-0">
          <div className="flex items-center gap-3 px-3 pb-2">
            <div className="h-8 w-8 rounded-full bg-slate-900 flex items-center justify-center text-white text-xs font-bold overflow-hidden">
              {profilePicture ? <img src={profilePicture} alt={username || ""} className="h-full w-full object-cover" /> : initials}
            </div>
            <span className="truncate text-sm font-medium text-slate-900">{username || t("user.fallbackName")}</span>
          </div>
          {[
            { name: t("user.settings"), href: "/settings", icon: Settings },
          ].map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              onClick={onItemClick}
              className={({ isActive }) =>
                cn(
                  "flex min-h-11 items-center rounded-md px-3 text-sm font-medium active:bg-slate-100",
                  isActive ? "bg-slate-100 font-semibold text-slate-900" : "text-slate-600"
                )
              }
            >
              <item.icon className="mr-3 h-5 w-5" aria-hidden="true" />
              {item.name}
            </NavLink>
          ))}
          <button
            type="button"
            onClick={() => {
              onItemClick?.()
              logout()
            }}
            className="flex min-h-11 w-full items-center rounded-md px-3 text-sm font-medium text-red-600 active:bg-red-50"
          >
            <LogOut className="mr-3 h-5 w-5" aria-hidden="true" />
            {t("user.logout")}
          </button>
        </div>
      ) : (
      <div className="border-t px-4 py-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex w-full items-center gap-3 px-2 py-1.5 rounded-md hover:bg-slate-100 transition-colors text-left outline-hidden">
              <div className="h-8 w-8 rounded-full bg-slate-900 flex items-center justify-center text-white text-xs font-bold overflow-hidden">
                {profilePicture ? (
                  <img src={profilePicture} alt={username || ""} className="h-full w-full object-cover" />
                ) : (
                  initials
                )}
              </div>
              <div className="flex flex-col flex-1 min-w-0">
                <span className="text-sm font-medium text-slate-900 truncate">{username || t("user.fallbackName")}</span>
                <span className="text-xs text-slate-500 truncate">{t("user.role")}</span>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="right" align="end" className="w-56 max-md:mb-2">
            <DropdownMenuLabel>{t("user.myAccount")}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <NavLink to="/settings">
              <DropdownMenuItem className="cursor-pointer">
                <Settings className="mr-2 h-4 w-4" />
                <span>{t("user.settings")}</span>
              </DropdownMenuItem>
            </NavLink>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-red-600 focus:text-red-600 cursor-pointer">
              <LogOut className="mr-2 h-4 w-4" />
              <span>{t("user.logout")}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      )}
    </div>
  )
}
