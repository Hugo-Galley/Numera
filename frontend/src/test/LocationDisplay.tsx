/** Affiche l'adresse courante du routeur, pour vérifier une redirection (« /month/bilan?year=2026 »). */
import { Outlet, useLocation } from "react-router-dom"

export function LocationDisplay() {
  const { pathname, search } = useLocation()
  return <output aria-label="adresse">{pathname + search}</output>
}

/** Page factice : un titre et l'adresse courante (avec `<Outlet />` pour une route parente). */
export function stubPage(title: string) {
  return function StubPage() {
    return (
      <div>
        <h1>{title}</h1>
        <LocationDisplay />
        <Outlet />
      </div>
    )
  }
}
