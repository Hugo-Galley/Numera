import { useEffect, useState } from "react"

/** true sous le breakpoint `md` (768 px). Pour les cas où CSS seul ne suffit pas (props Recharts). */
export function useIsMobile(): boolean {
  const query = "(max-width: 767px)"
  const [mobile, setMobile] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia(query).matches : false
  )
  useEffect(() => {
    const mql = window.matchMedia(query)
    const onChange = () => setMobile(mql.matches)
    onChange()
    mql.addEventListener("change", onChange)
    return () => mql.removeEventListener("change", onChange)
  }, [])
  return mobile
}
