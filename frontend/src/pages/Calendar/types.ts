

export interface CalendarEvent {
  id: string | number
  date: string
  name: string
  amount: number
  type: string
  category_id: number | null
  is_projected: boolean
  currency: string
  recurring_id?: number
  logo?: string | null
  ticker?: string
  quantity?: number
  unit_price?: number
}

export interface DailyBalance {
  date: string
  balance: number
}

export interface CalendarData {
  month: number
  year: number
  events: CalendarEvent[]
  daily_balances: DailyBalance[]
}

export interface Account {
  id: number
  name: string
  currency: string
  type: string
}

/** `embedded` : affiché dans l'onglet Calendrier de la page Échéances (titre et raccourci vers les
 * récurrences inutiles, ils sont déjà sur la page). */
