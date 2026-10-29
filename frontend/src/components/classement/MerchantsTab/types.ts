

export type MerchantAlias = {
  id: number
  merchant_id: number
  label: string
}

export type Merchant = {
  id: number
  name: string
  category_id: number | null
  icon: string | null
  color: string | null
  aliases: MerchantAlias[]
}

export type Category = {
  id: number
  name: string
  color?: string
}

export type Suggestion = {
  label: string
  count: number
}

export const COLOR_OPTIONS = [
  { name: "Emerald", value: "#10b981" },
  { name: "Blue", value: "#3b82f6" },
  { name: "Indigo", value: "#6366f1" },
  { name: "Violet", value: "#8b5cf6" },
  { name: "Pink", value: "#ec4899" },
  { name: "Rose", value: "#f43f5e" },
  { name: "Orange", value: "#f97316" },
  { name: "Amber", value: "#f59e0b" },
  { name: "Slate", value: "#64748b" },
  { name: "Black", value: "#0f172a" },
]
