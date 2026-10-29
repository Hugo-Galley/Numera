

export type Account = {
  id: number
  name: string
  type: "courant" | "epargne" | "investissement" | "assurance_vie" | "credit"
  currency: string
  active: boolean
  asset_class?: string
  sector?: string
  geographic_zone?: string
  institution?: string
  logo?: string | null
  is_main?: boolean
  fonds_euros_pct?: number
  fonds_investis_pct?: number
  valuation_mode?: "positions" | "snapshot"
  tax_wrapper?: "pea" | "per" | "cto" | "assurance_vie" | "livret_a" | "livret_jeune" | "pee" | "ldds" | "lep" | null
  opened_at?: string | null
  balance?: number
}

export const TAX_WRAPPERS = [
  { value: "pea", label: "PEA" },
  { value: "per", label: "PER" },
  { value: "cto", label: "CTO" },
  { value: "assurance_vie", label: "Assurance-vie" },
  { value: "livret_a", label: "Livret A" },
  { value: "livret_jeune", label: "Livret Jeune" },
  { value: "ldds", label: "LDDS" },
  { value: "lep", label: "LEP" },
  { value: "pee", label: "PEE" },
] as const

export type TaxWrapper = (typeof TAX_WRAPPERS)[number]["value"]
