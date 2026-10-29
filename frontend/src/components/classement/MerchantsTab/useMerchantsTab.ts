
import { useMerchantsData } from "./useMerchantsData"

/** Assemble l'état, les chargements et les actions de MerchantsTab. */
export function useMerchantsTab() {
  const merchantsData = useMerchantsData()
  return { ...merchantsData }
}

export type MerchantsTabCtx = ReturnType<typeof useMerchantsTab>
