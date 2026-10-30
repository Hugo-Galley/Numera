/** Handlers par défaut, un fichier par domaine (même découpage que `lib/api/<domaine>.ts`). */
import { accountsHandlers } from "./accounts"
import { analyticsHandlers } from "./analytics"
import { authHandlers } from "./auth"
import { classementHandlers } from "./classement"
import { investmentsHandlers } from "./investments"
import { recurringHandlers } from "./recurring"
import { savingsHandlers } from "./savings"
import { transactionsHandlers } from "./transactions"

export const handlers = [
  ...authHandlers,
  ...accountsHandlers,
  ...transactionsHandlers,
  ...classementHandlers,
  ...recurringHandlers,
  ...savingsHandlers,
  ...investmentsHandlers,
  ...analyticsHandlers,
]

export { apiUrl } from "./apiUrl"
