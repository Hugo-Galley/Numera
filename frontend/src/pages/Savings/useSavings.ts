import { useSavingsData } from "./useSavingsData"

/** Assemble l'état, les chargements et les actions de Savings. */
export function useSavings() {
  const savingsData = useSavingsData()
  return { ...savingsData }
}

export type SavingsCtx = ReturnType<typeof useSavings>
