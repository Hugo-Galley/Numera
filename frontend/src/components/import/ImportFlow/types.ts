import type { ApiResponse } from "@/lib/api/types"



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

/** Réponse de l'aperçu d'import, telle que le contrat de l'API la décrit (lignes comprises). */
export type PreviewData = ApiResponse<"/import/preview", "post">


export type ImportFlowProps = {
  /** Compte présélectionné (import depuis la page d'un compte) */
  accountId?: number
  /** Appelé après un import qui a inséré au moins une ligne */
  onImported?: () => void
}
