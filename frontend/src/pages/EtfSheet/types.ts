import type { ApiResponse } from "@/lib/api/types"

/** Contrat de `/etf-profiles/{id}/constituents`. */
export type EtfSheet = ApiResponse<"/etf-profiles/{profile_id}/constituents", "get">
export type EtfSheetLine = EtfSheet["lines"][number]
export type EtfWeight = EtfSheet["countries"][number]
