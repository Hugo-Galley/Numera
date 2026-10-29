import { useAccountsState } from "./useAccountsState"
import { useAccountsActions } from "./useAccountsActions"

/** Assemble l'état, les chargements et les actions de Accounts. */
export function useAccounts() {
  const accountsState = useAccountsState()
  const accountsActions = useAccountsActions({ ...accountsState })
  return { ...accountsState, ...accountsActions }
}

export type AccountsCtx = ReturnType<typeof useAccounts>
