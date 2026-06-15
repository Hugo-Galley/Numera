import { useState } from "react"
import { NavLink } from "react-router-dom"
import { 
  LayoutDashboard, 
  Wallet, 
  TrendingUp, 
  Upload, 
  Settings,
  CreditCard,
  PiggyBank,
  Eye, 
  EyeOff,
  ArrowLeftRight,
  LogOut,
  Search,
  CalendarDays,
  Repeat,
  Sparkles,
  ShieldCheck,
  User,
  ChevronDown,
  ChevronRight
} from "lucide-react"
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

const navigationGroups = [
  {
    title: "Vue d'ensemble",
    items: [
      { name: "Tableau de bord", href: "/", icon: LayoutDashboard },
      { name: "Bilan Mensuel", href: "/report", icon: Sparkles },
    ]
  },
  {
    title: "Patrimoine",
    items: [
      { name: "Comptes", href: "/accounts", icon: Wallet },
      { name: "Épargne", href: "/savings", icon: PiggyBank },
      { name: "Investissements", href: "/investments", icon: TrendingUp },
    ]
  },
  {
    title: "Analyse & Outils",
    items: [
      { name: "Comparaison", href: "/comparison", icon: ArrowLeftRight },
      { name: "Calendrier", href: "/calendar", icon: CalendarDays },
      { name: "Récurrences", href: "/recurring", icon: Repeat },
      { name: "Centre d'actions", href: "/audit", icon: ShieldCheck },
    ]
  }
]

export function Sidebar({ className, onItemClick }: { className?: string, onItemClick?: () => void }) {
  const { isPrivacyMode, togglePrivacyMode, setSearchOpen } = useUI()
  const { logout, username, profile } = useAuth()
  
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    "Vue d'ensemble": true,
    "Patrimoine": true,
    "Analyse & Outils": false,
  })

  const toggleGroup = (title: string) => {
    setOpenGroups(prev => ({ ...prev, [title]: !prev[title] }))
  }

  const initials = username ? username.slice(0, 2).toUpperCase() : "?"
  const profilePicture = profile?.profile_picture_url

  return (
    <div className={cn("flex flex-col bg-white", className)}>
      <div className="flex h-16 items-center border-b px-6">
        <CreditCard className="h-6 w-6 mr-2" />
        <span className="text-lg font-bold tracking-tight">Suivi Budget</span>
      </div>
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-4 px-3">
          {navigationGroups.map((group, i) => (
            <div key={i} className="space-y-1">
              <button
                onClick={() => toggleGroup(group.title)}
                className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider hover:bg-slate-50 rounded-md transition-colors"
              >
                <span>{group.title}</span>
                {openGroups[group.title] ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
              
              <div className={cn(
                "space-y-1 overflow-hidden transition-all duration-200 ease-in-out",
                openGroups[group.title] ? "max-h-96 opacity-100 pt-1" : "max-h-0 opacity-0"
              )}>
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
          <DropdownMenuContent side="right" align="end" className="w-56">
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
    </div>
  )
}
