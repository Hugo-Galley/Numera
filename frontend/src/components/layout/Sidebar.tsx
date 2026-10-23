import { useEffect, useRef, useState } from "react"
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
  User,
  ClipboardCheck,
  Gift,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
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

// 11 entrées en 3 groupes toujours ouverts : Bilan, Revue et Comparaison sont des onglets de « Mois »,
// le calendrier et le salaire des onglets d'« Échéances ».
const navigationGroups = [
  {
    title: "Vue d'ensemble",
    items: [
      { name: "Tableau de bord", href: "/", icon: LayoutDashboard },
      { name: "Mois", href: "/month", icon: ClipboardCheck },
      { name: "Bilan annuel", href: "/wrapped", icon: Gift },
      { name: "Centre d'actions", href: "/audit", icon: ShieldCheck, badge: "actions" as const },
    ]
  },
  {
    title: "Patrimoine",
    items: [
      { name: "Comptes", href: "/accounts", icon: Wallet },
      { name: "Épargne", href: "/savings", icon: PiggyBank },
      { name: "Investissements", href: "/investments", icon: TrendingUp },
      { name: "Fiscalité", href: "/tax", icon: Landmark },
    ]
  },
  {
    title: "Gestion",
    items: [
      { name: "Échéances", href: "/recurring", icon: Repeat },
      { name: "Remboursements", href: "/reimbursements", icon: HandCoins },
      { name: "Simulateur", href: "/tools", icon: Calculator },
    ]
  }
]

/** Nombre d'actions urgentes du Centre d'actions, relu au plus une fois par minute en naviguant. */
function useUrgentActionCount(): number {
  const { pathname } = useLocation()
  const [count, setCount] = useState(0)
  const lastFetch = useRef(0)

  useEffect(() => {
    if (Date.now() - lastFetch.current < 60_000) return
    lastFetch.current = Date.now()
    api.get<{ summary: { high_priority: number } }>("/analytics/actions")
      .then((data) => setCount(data.summary.high_priority))
      .catch(() => {})
  }, [pathname])

  return count
}

export function Sidebar({ className, onItemClick, hideBrand }: { className?: string, onItemClick?: () => void, hideBrand?: boolean }) {
  const { isPrivacyMode, togglePrivacyMode, setSearchOpen } = useUI()
  const { logout, username, profile } = useAuth()
  
  const urgentActions = useUrgentActionCount()

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
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-4 px-3">
          {navigationGroups.map((group, i) => (
            <div key={i} className="space-y-1">
              <p className="px-3 pt-2 pb-1 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                {group.title}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    onClick={onItemClick}
                    className={({ isActive }) =>
                      cn(
                        "group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-slate-100 text-slate-900"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      )
                    }
                  >
                    <item.icon
                      className={cn(
                        "mr-3 h-5 w-5 flex-shrink-0 transition-colors",
                        "group-hover:text-slate-900"
                      )}
                      aria-hidden="true"
                    />
                    {item.name}
                    {"badge" in item && urgentActions > 0 && (
                      <span
                        className="ml-auto rounded-full bg-rose-600 px-2 py-0.5 text-[10px] font-bold text-white"
                        aria-label={`${urgentActions} actions urgentes`}
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
      <div className="px-3 py-4 border-t flex gap-2">
        <Button 
          variant="outline" 
          size="sm" 
          className="flex-1 justify-start gap-2 text-slate-600 border-slate-200 px-3"
          onClick={togglePrivacyMode}
        >
          {isPrivacyMode ? (
            <>
              <Eye className="h-4 w-4" />
              <span className="truncate">Afficher</span>
            </>
          ) : (
            <>
              <EyeOff className="h-4 w-4" />
              <span className="truncate">Masquer</span>
            </>
          )}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="px-3 text-slate-600 border-slate-200"
          onClick={() => setSearchOpen(true)}
        >
          <Search className="h-4 w-4" />
        </Button>
      </div>
      {hideBrand ? (
        // Menu mobile (feuille du bas) : un menu déroulant s'y superposerait à une 2e couche modale, on liste les actions à plat
        <div className="border-t p-3 pb-4">
          <div className="flex items-center gap-3 px-3 pb-2">
            <div className="h-8 w-8 rounded-full bg-slate-900 flex items-center justify-center text-white text-xs font-bold overflow-hidden">
              {profilePicture ? <img src={profilePicture} alt={username || ""} className="h-full w-full object-cover" /> : initials}
            </div>
            <span className="truncate text-sm font-medium text-slate-900">{username || "Utilisateur"}</span>
          </div>
          {[
            { name: "Paramètres généraux", href: "/settings", icon: Settings },
            { name: "Profil & Compte", href: "/settings?tab=account", icon: User },
          ].map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              onClick={onItemClick}
              className="flex min-h-11 items-center rounded-md px-3 text-sm font-medium text-slate-600 active:bg-slate-100"
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
            Se déconnecter
          </button>
        </div>
      ) : (
      <div className="border-t p-4">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex w-full items-center gap-3 px-2 py-1.5 rounded-md hover:bg-slate-100 transition-colors text-left outline-none">
              <div className="h-8 w-8 rounded-full bg-slate-900 flex items-center justify-center text-white text-xs font-bold overflow-hidden">
                {profilePicture ? (
                  <img src={profilePicture} alt={username || ""} className="h-full w-full object-cover" />
                ) : (
                  initials
                )}
              </div>
              <div className="flex flex-col flex-1 min-w-0">
                <span className="text-sm font-medium text-slate-900 truncate">{username || "Utilisateur"}</span>
                <span className="text-xs text-slate-500 truncate">Administrateur</span>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="right" align="end" className="w-56 max-md:mb-2">
            <DropdownMenuLabel>Mon Compte</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <NavLink to="/settings">
              <DropdownMenuItem className="cursor-pointer">
                <Settings className="mr-2 h-4 w-4" />
                <span>Paramètres généraux</span>
              </DropdownMenuItem>
            </NavLink>
            <NavLink to="/settings?tab=account">
              <DropdownMenuItem className="cursor-pointer">
                <User className="mr-2 h-4 w-4" />
                <span>Profil & Compte</span>
              </DropdownMenuItem>
            </NavLink>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-red-600 focus:text-red-600 cursor-pointer">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Se déconnecter</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      )}
    </div>
  )
}
