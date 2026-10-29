import { HoldingsTableProps } from "./types"
import { useHoldingsState } from "./useHoldingsState"

/** Assemble l'état, les chargements et les actions de HoldingsTable. */
export function useHoldingsTable(accountId: HoldingsTableProps["accountId"], accountName: HoldingsTableProps["accountName"], holdings: HoldingsTableProps["holdings"], onRefresh: HoldingsTableProps["onRefresh"], onAddDividend: HoldingsTableProps["onAddDividend"]) {
  const holdingsState = useHoldingsState({ accountId, accountName, holdings, onRefresh, onAddDividend })
  return { accountId, accountName, holdings, onRefresh, onAddDividend, ...holdingsState }
}

export type HoldingsTableCtx = ReturnType<typeof useHoldingsTable>
