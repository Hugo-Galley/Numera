/** Petites fabriques typées : valeurs par défaut plausibles, surchargées champ par champ. */
import type { ActionCenterData } from "@/pages/Audit/types"
import type { Account, Category, Transaction } from "@/pages/AccountDetail/types"

let nextId = 1
const id = () => nextId++

export function makeAccount(overrides: Partial<Account> = {}): Account {
  return { id: id(), name: "Compte courant", type: "courant", currency: "EUR", balance: 1000, ...overrides }
}

export function makeCategory(overrides: Partial<Category> = {}): Category {
  return { id: id(), name: "Courses", type: "depense", color: "#10b981", archived: false, ...overrides }
}

export function makeTransaction(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: id(),
    account_id: 1,
    date: "2026-06-15T10:00:00",
    type: "Sortie",
    merchant: "Carrefour",
    merchant_id: null,
    amount: 42.5,
    currency: "EUR",
    original_amount: 42.5,
    running_balance: 957.5,
    category_id: null,
    category: null,
    tags: [],
    note: null,
    is_recurring: false,
    custom_icon: null,
    custom_color: null,
    ...overrides,
  }
}

export function makeProfile(overrides: Partial<{ username: string; profile_picture_url: string | null; mcp_enabled: boolean; privacy_on_start: boolean }> = {}) {
  return { username: "admin", profile_picture_url: null, mcp_enabled: false, privacy_on_start: false, ...overrides }
}

export function makeActionCenter(overrides: Partial<ActionCenterData> = {}): ActionCenterData {
  return {
    summary: { total_actions: 0, high_priority: 0, medium_priority: 0, low_priority: 0, checked_at: "2026-06-15T10:00:00" },
    actions: [],
    ...overrides,
  }
}
