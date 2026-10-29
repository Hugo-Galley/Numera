
import { useCategoriesData } from "./useCategoriesData"

/** Assemble l'état, les chargements et les actions de CategoriesTab. */
export function useCategoriesTab() {
  const categoriesData = useCategoriesData()
  return { ...categoriesData }
}

export type CategoriesTabCtx = ReturnType<typeof useCategoriesTab>
