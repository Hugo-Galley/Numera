import { Navigate, useLocation } from "react-router-dom"

/** Ancienne adresse → nouvel emplacement, en gardant les paramètres (`?year=&month=`…). */
export function RedirectKeepingSearch({ to }: { to: string }) {
  const { search } = useLocation()
  const [pathname, extra] = to.split("?")
  const params = new URLSearchParams(search)
  new URLSearchParams(extra ?? "").forEach((value, key) => params.set(key, value))
  const query = params.toString()
  return <Navigate to={{ pathname, search: query ? `?${query}` : "" }} replace />
}
