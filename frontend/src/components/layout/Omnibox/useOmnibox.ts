
import { useOmniboxSearch } from "./useOmniboxSearch"

/** Assemble l'état, les chargements et les actions de Omnibox. */
export function useOmnibox() {
  const omniboxSearch = useOmniboxSearch()
  return { ...omniboxSearch }
}

export type OmniboxCtx = ReturnType<typeof useOmnibox>
