/** Types du contrat de l'API pour la recherche de titres et les profils ETF. */
import type { ApiResponse } from "@/lib/api/types"

/**
 * Résultat de recherche de titre. Le contrat OpenAPI ne déclare pas `price`, `price_eur` ni `is_etf` (le backend ne les
 * renvoie pas toujours) : ils restent optionnels ici, en type local minimal.
 */
export type MarketAsset = Partial<ApiResponse<"/market/search", "get">[number]> &
  Pick<ApiResponse<"/market/search", "get">[number], "symbol" | "name"> & {
    price?: number | null
    price_eur?: number | null
    is_etf?: boolean
  }
export type MarketQuote = ApiResponse<"/market/quote", "get">[string]
export type EtfProfile = ApiResponse<"/etf-profiles/auto-decompose", "post">
