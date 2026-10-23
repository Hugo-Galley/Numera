import { Suspense, useRef } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { Omnibox } from "./Omnibox"
import { Toaster } from "@/components/ui/sonner"
import { Button } from "@/components/ui/button"
import { CreditCard, Eye, EyeOff, Search } from "lucide-react"
import { MobileNav } from "./MobileNav"
import { useUI } from "@/providers/UIProvider"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import { PageLoader } from "./PageLoader"
import { PwaExtras } from "./PwaExtras"

export function AppLayout() {
  const { isPrivacyMode, togglePrivacyMode, setSearchOpen } = useUI()
  const mainRef = useRef<HTMLElement>(null)

  return (
    <WorkTimeProvider>
      <div className="flex h-dvh w-full overflow-x-hidden bg-slate-50/50 flex-col md:flex-row">
        {/* En-tête mobile : marque + confidentialité + recherche ; la navigation est dans MobileNav */}
        <header className="flex h-14 items-center justify-between border-b bg-white px-4 md:hidden shrink-0 pt-[env(safe-area-inset-top)] box-content">
          <div className="flex items-center">
            <CreditCard className="h-5 w-5 mr-2" />
            <span className="text-lg font-bold tracking-tight text-slate-900">Numera</span>
          </div>
          <div className="flex items-center">
            <Button variant="ghost" size="icon" className="h-11 w-11" onClick={togglePrivacyMode} aria-label={isPrivacyMode ? "Afficher les montants" : "Masquer les montants"}>
              {isPrivacyMode ? <Eye className="h-5 w-5" /> : <EyeOff className="h-5 w-5" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-11 w-11" onClick={() => setSearchOpen(true)} aria-label="Rechercher">
              <Search className="h-5 w-5" />
            </Button>
          </div>
        </header>

        {/* Desktop Sidebar */}
        <Sidebar className="hidden md:flex h-full w-64 border-r shrink-0" />

        {/* Main Content */}
        <main ref={mainRef} className="flex-1 overscroll-y-contain min-w-0 overflow-y-auto overflow-x-hidden pb-[calc(4rem+env(safe-area-inset-bottom))] md:pb-0">
          <div className="container mx-auto p-4 md:p-8 max-w-7xl">
            {/* Le menu reste affiché pendant le chargement d'une page */}
            <Suspense fallback={<PageLoader />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
        <PwaExtras scrollRef={mainRef} />
        <MobileNav />
        <Omnibox />
        <Toaster />
      </div>
    </WorkTimeProvider>
  )
}
