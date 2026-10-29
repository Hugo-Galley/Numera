

export interface WealthSimulatorProps {
  initialCapitalDefault?: number
}

export interface LifeEvent {
  year: number
  amount: number
  label: string
}

export interface AssetClass {
  id: string
  name: string
  pct: number
  expectedReturn: number
  volatility: number
}

export const defaultAssetClasses: AssetClass[] = [
  { id: "1", name: "Actions / ETF World", pct: 60, expectedReturn: 8, volatility: 15 },
  { id: "2", name: "Obligations d'État", pct: 20, expectedReturn: 3.5, volatility: 5 },
  { id: "3", name: "Immobilier SCPI", pct: 10, expectedReturn: 5.5, volatility: 8 },
  { id: "4", name: "Cash / Fonds Euro", pct: 10, expectedReturn: 2, volatility: 0 }
]
