import { ImportFlowProps } from "./types"
import { useImportState } from "./useImportState"

/** Assemble l'état, les chargements et les actions de ImportFlow. */
export function useImportFlow(accountId: ImportFlowProps["accountId"], onImported: ImportFlowProps["onImported"]) {
  const importState = useImportState({ accountId, onImported })
  return { accountId, onImported, ...importState }
}

export type ImportFlowCtx = ReturnType<typeof useImportFlow>
