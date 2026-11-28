/** Handlers par défaut, un fichier par domaine (même découpage que `lib/api/<domaine>.ts`). */
import { accountsHandlers } from "./accounts"
import { analyticsHandlers } from "./analytics"
import { authHandlers } from "./auth"
import { classementHandlers } from "./classement"
import { investmentsHandlers } from "./investments"
import { monthReviewHandlers } from "./monthReview"
import { recurringHandlers } from "./recurring"
import { savingsHandlers } from "./savings"
import { settingsHandlers } from "./settings"
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
  ...monthReviewHandlers,
  ...settingsHandlers,
]

export { apiUrl } from "./apiUrl"
