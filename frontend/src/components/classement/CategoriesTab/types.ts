

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

export type Category = {
  id: number
  name: string
  type: "depense" | "revenu" | "neutre"
  icon?: string
  color?: string
  group?: string | null
  monthly_limit?: number | null
  annual_limit?: number | null
  archived?: boolean
}
