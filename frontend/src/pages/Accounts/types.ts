

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
  { value: "pea" },
  { value: "per" },
  { value: "cto" },
  { value: "assurance_vie" },
  { value: "livret_a" },
  { value: "livret_jeune" },
  { value: "ldds" },
  { value: "lep" },
  { value: "pee" },
] as const

export type TaxWrapper = (typeof TAX_WRAPPERS)[number]["value"]
