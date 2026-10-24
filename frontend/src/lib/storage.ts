/**
 * `localStorage` peut lever (navigation privée, données de site bloquées) ou être absent.
 * Ce wrapper ne lève jamais : à défaut, les valeurs vivent en mémoire pour la durée de l'onglet.
 */
const memory = new Map<string, string>()

export const safeStorage = {
  getItem(key: string): string | null {
    try {
      return window.localStorage.getItem(key)
    } catch {
      return memory.get(key) ?? null
    }
  },
  setItem(key: string, value: string): void {
    try {
      window.localStorage.setItem(key, value)
    } catch {
      memory.set(key, value)
    }
  },
  removeItem(key: string): void {
    try {
      window.localStorage.removeItem(key)
    } catch {
      /* indisponible */
    }
    memory.delete(key)
  },
}
