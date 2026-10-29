import { useInvestmentsData } from "./useInvestmentsData"

/** Assemble l'état, les chargements et les actions de Investments. */
export function useInvestments() {
  const investmentsData = useInvestmentsData()
  return { ...investmentsData }
}

export type InvestmentsCtx = ReturnType<typeof useInvestments>
