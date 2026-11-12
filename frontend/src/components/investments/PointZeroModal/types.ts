

export interface BaselineRow {
  ticker: string
  asset_name: string
  isin?: string | null
  quantity: number
  buy_price_avg?: number | null
  currency: string
  etf_profile_id?: number | null
  is_etf: boolean
  current_price?: number | null
  current_price_eur?: number | null
  is_suggestion?: boolean
}

export interface PointZeroModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  accountId: number
  accountName: string
  onBaselineSaved: () => void
}
