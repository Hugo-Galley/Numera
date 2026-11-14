import type { Language } from "@/i18n"
import { putNotificationsSettings } from "@/lib/api/settings"

/**
 * Enregistre la langue de l'interface côté serveur : les notifications partent d'une tâche de fond, sans en-tête
 * `Accept-Language`, et lisent cette valeur. Sans conséquence si l'appel échoue (le serveur garde l'ancienne langue).
 */
export async function syncServerLanguage(language: Language): Promise<void> {
  try {
    await putNotificationsSettings({ language })
  } catch (error) {
    console.warn("Server language not saved", error)
  }
}
