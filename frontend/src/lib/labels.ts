/** Libellés affichés des valeurs techniques stockées en base, dans la langue de l'interface. */
import i18n from "i18next"

const ACCOUNT_TYPES = ["courant", "epargne", "investissement", "assurance_vie", "credit", "bank"] as const
const CATEGORY_TYPES = ["depense", "revenu", "neutre"] as const

export function accountTypeLabel(type: string | null | undefined) {
  if (!type) return i18n.t("accountTypes.other", { ns: "common" })
  const known = ACCOUNT_TYPES.find((t) => t === type)
  return known ? i18n.t(`accountTypes.${known}`, { ns: "common" }) : type.charAt(0).toUpperCase() + type.slice(1)
}

export const categoryTypeLabel = (type: string) => {
  const known = CATEGORY_TYPES.find((t) => t === type)
  return known ? i18n.t(`categoryTypes.${known}`, { ns: "common" }) : type
}
