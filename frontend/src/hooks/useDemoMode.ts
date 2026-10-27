import { useEffect, useState } from "react"
import { API_BASE } from "@/lib/api"

// Identifiants publics de l'instance de démonstration (cf. docker-compose.demo.yml)
export const DEMO_CREDENTIALS = { username: "demo", password: "demo" }

// /health est public : une seule requête par chargement de l'app
let demoPromise: Promise<boolean> | null = null

function fetchDemoMode(): Promise<boolean> {
  demoPromise ??= fetch(`${API_BASE}/health`)
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => !!d?.demo)
    .catch(() => false)
  return demoPromise
}

/** Vrai si le backend tourne en mode démo (données fictives, régénérées chaque jour). */
export function useDemoMode(): boolean {
  const [demo, setDemo] = useState(false)
  useEffect(() => {
    let alive = true
    fetchDemoMode().then((value) => alive && setDemo(value))
    return () => {
      alive = false
    }
  }, [])
  return demo
}
