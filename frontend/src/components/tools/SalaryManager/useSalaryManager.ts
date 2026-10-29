
import { useSalaryData } from "./useSalaryData"

/** Assemble l'état, les chargements et les actions de SalaryManager. */
export function useSalaryManager() {
  const salaryData = useSalaryData()
  return { ...salaryData }
}

export type SalaryManagerCtx = ReturnType<typeof useSalaryManager>
