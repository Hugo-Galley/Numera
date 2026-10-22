import { Suspense } from "react"
import { NavLink, Outlet } from "react-router-dom"
import { PageLoader } from "@/components/layout/PageLoader"
import { cn } from "@/lib/utils"

const TABS = [
  { to: "bilan", label: "Bilan" },
  { to: "revue", label: "Revue" },
  { to: "comparaison", label: "Comparaison" },
]

/** Espace « Mois » : bilan, revue de fin de mois et comparaison, en sous-routes pour que chaque page
 * garde ses propres paramètres d'URL (`?year=&month=` de la revue). */
export default function MonthHub() {
  return (
    <div className="space-y-6">
      <nav className="inline-flex rounded-lg bg-slate-100 p-1">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              cn(
                "rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
                isActive ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Suspense fallback={<PageLoader />}>
        <Outlet />
      </Suspense>
    </div>
  )
}
