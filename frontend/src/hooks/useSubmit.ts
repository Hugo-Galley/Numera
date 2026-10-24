import { useCallback, useRef, useState } from "react"

/**
 * Protège une action asynchrone (création, enregistrement…) contre la double soumission :
 * un second appel pendant que le premier est en cours est ignoré. Retourne l'action protégée
 * et un état `busy` pour désactiver le bouton.
 *
 * Le verrou est un `ref` (synchrone) : deux clics dans la même frame sont bien dédoublonnés,
 * ce qu'un simple `useState` ne garantit pas.
 */
export function useSubmit<A extends unknown[]>(
  action: (...args: A) => Promise<unknown>
): [(...args: A) => Promise<void>, boolean] {
  const running = useRef(false)
  const actionRef = useRef(action)
  actionRef.current = action
  const [busy, setBusy] = useState(false)

  const guarded = useCallback(async (...args: A) => {
    if (running.current) return
    running.current = true
    setBusy(true)
    try {
      await actionRef.current(...args)
    } finally {
      running.current = false
      setBusy(false)
    }
  }, [])

  return [guarded, busy]
}
