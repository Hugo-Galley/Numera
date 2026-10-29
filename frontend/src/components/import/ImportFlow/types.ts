

export type Account = {
  id: number
  name: string
  type: string
  active: boolean
}

export type Category = {
  id: number
  name: string
}

export type PreviewData = {
  filename: string
  total_rows: number
  invalid_rows: number
  warnings: string[]
  delimiter: string
  preview: any[]
  unknown_categories: string[]
}


export type ImportFlowProps = {
  /** Compte présélectionné (import depuis la page d'un compte) */
  accountId?: number
  /** Appelé après un import qui a inséré au moins une ligne */
  onImported?: () => void
}
