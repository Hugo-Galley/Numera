import { Fragment, type ReactNode } from "react"
import { useTranslation } from "react-i18next"

/**
 * Remonte l'arbre quand la langue change : les formats de dates et de montants (`appLocale()`) sont lus à l'appel,
 * donc les écrans pas encore migrés vers `useTranslation` se mettent aussi à jour.
 */
export function LanguageBoundary({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation()
  return <Fragment key={i18n.language}>{children}</Fragment>
}
