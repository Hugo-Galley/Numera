import { useCallback, useEffect, useState } from "react"
import { getEtfProfilesByIdConstituents } from "@/lib/api/investments"
import { resetApiCache } from "@/lib/apiCache"
import { errorMessage } from "@/lib/utils"
import type { EtfSheet } from "./types"

/** Charge la fiche d'un fonds ; une réponse arrivée après un changement d'adresse est ignorée. */
export function useEtfSheet(profileId: string, fallbackError: string) {
  const [state, setState] = useState<{ id: string; sheet?: EtfSheet; error?: string }>({ id: profileId })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    getEtfProfilesByIdConstituents(profileId)
      .then((sheet) => { if (!cancelled) setState({ id: profileId, sheet }) })
      .catch((error: unknown) => { if (!cancelled) setState({ id: profileId, error: errorMessage(error, fallbackError) }) })
    return () => { cancelled = true }
  }, [profileId, attempt, fallbackError])

  const retry = useCallback(() => {
    resetApiCache()
    setState({ id: profileId })
    setAttempt((n) => n + 1)
  }, [profileId])

  // La fiche d'un autre fonds ne reste jamais affichée pendant le chargement
  const current = state.id === profileId ? state : { id: profileId, sheet: undefined, error: undefined }
  return { sheet: current.sheet, error: current.error, retry }
}
