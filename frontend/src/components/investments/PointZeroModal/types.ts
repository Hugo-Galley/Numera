

export interface BaselineRow {
  ticker: string
  asset_name: string
  isin?: string
  quantity: number
  buy_price_avg?: number
  currency: string
  etf_profile_id?: number
  is_etf: boolean
  current_price?: number
  current_price_eur?: number
  is_suggestion?: boolean
}

export interface PointZeroModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  accountId: number
  accountName: string
  onBaselineSaved: () => void
}
