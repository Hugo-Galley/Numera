import { PointZeroModalProps } from "./types"
import { usePointZeroState } from "./usePointZeroState"

/** Assemble l'état, les chargements et les actions de PointZeroModal. */
export function usePointZeroModal(open: PointZeroModalProps["open"], onOpenChange: PointZeroModalProps["onOpenChange"], accountId: PointZeroModalProps["accountId"], accountName: PointZeroModalProps["accountName"], onBaselineSaved: PointZeroModalProps["onBaselineSaved"]) {
  const pointZeroState = usePointZeroState({ open, onOpenChange, accountId, accountName, onBaselineSaved })
  return { open, onOpenChange, accountId, accountName, onBaselineSaved, ...pointZeroState }
}

export type PointZeroModalCtx = ReturnType<typeof usePointZeroModal>
