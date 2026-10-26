/** Libellés affichés des valeurs techniques stockées en base. */

export function accountTypeLabel(type: string | null | undefined) {
  switch (type) {
    case "courant": return "Compte Courant"
    case "epargne": return "Épargne"
    case "investissement": return "Investissement"
    case "assurance_vie": return "Assurance-Vie"
    case "credit": return "Crédit"
    case "bank": return "Compte bancaire"
    default: return type ? type.charAt(0).toUpperCase() + type.slice(1) : "Autre"
  }
}

const CATEGORY_TYPE_LABELS: Record<string, string> = { depense: "Dépense", revenu: "Revenu", neutre: "Neutre" }

export const categoryTypeLabel = (type: string) => CATEGORY_TYPE_LABELS[type] ?? type
