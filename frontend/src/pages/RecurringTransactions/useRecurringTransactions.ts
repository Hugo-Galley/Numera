import { useRecurringState } from "./useRecurringState"
import { useRecurringForm } from "./useRecurringForm"
import { useRecurringActions } from "./useRecurringActions"

/** Assemble l'état, les chargements et les actions de RecurringTransactions. */
export function useRecurringTransactions() {
  const recurringState = useRecurringState()
  const recurringForm = useRecurringForm({ ...recurringState })
  const recurringActions = useRecurringActions({ ...recurringState, ...recurringForm })
  return { ...recurringState, ...recurringForm, ...recurringActions }
}

export type RecurringTransactionsCtx = ReturnType<typeof useRecurringTransactions>
