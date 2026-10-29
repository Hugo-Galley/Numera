
import { useTaxData } from "./useTaxData"

/** Assemble l'état, les chargements et les actions de Tax. */
export function useTax() {
  const taxData = useTaxData()
  return { ...taxData }
}

export type TaxCtx = ReturnType<typeof useTax>
