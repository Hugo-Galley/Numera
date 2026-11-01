import { QueryClient } from "@tanstack/react-query"

/** Durée pendant laquelle une lecture identique est resservie sans requête (les tâches de fond du serveur restent visibles après ce délai). */
export const API_CACHE_MS = 30_000

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: API_CACHE_MS, gcTime: 2 * API_CACHE_MS, retry: false, refetchOnWindowFocus: false } },
})

// Générations : une lecture lancée avant une écriture finit sous l'ancienne clé et n'est plus jamais relue.
let generation = 0

export function cacheKey(endpoint: string): readonly unknown[] {
  return ["api", generation, endpoint]
}

/**
 * Invalide le cache (écriture, déconnexion, session expirée, rechargement demandé). On change de génération au lieu de
 * `queryClient.clear()`, qui annulerait les lectures en vol (`CancelledError` à la place de leur résultat ou de leur
 * `ApiError`) ; les anciennes entrées ne sont plus lues et expirent avec `gcTime`.
 */
export function resetApiCache(): void {
  generation += 1
}

/**
 * Lecture mise en cache et dédoublonnée. La copie rendue (`structuredClone`) protège le cache : les pages
 * trient et modifient volontiers les tableaux reçus.
 */
export async function cachedRead<T>(endpoint: string, read: () => Promise<T>): Promise<T> {
  const data = await queryClient.fetchQuery({ queryKey: cacheKey(endpoint), queryFn: read })
  return data == null ? data : structuredClone(data)
}
