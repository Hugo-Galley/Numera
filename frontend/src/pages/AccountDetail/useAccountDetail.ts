import { useAccountDetailState } from "./useAccountDetailState"
import { useAccountForms } from "./useAccountForms"
import { useAccountDetailData } from "./useAccountDetailData"
import { useTransactionActions } from "./useTransactionActions"
import { useInvestmentActions } from "./useInvestmentActions"
import { useTransactionView } from "./useTransactionView"
import type { Account } from "./types"

/** Assemble l'état, les chargements et les actions de la page d'un compte. */
export function useAccountDetail() {
  const accountDetailState = useAccountDetailState()
  const accountForms = useAccountForms({ ...accountDetailState })
  const accountDetailData = useAccountDetailData({ ...accountDetailState, ...accountForms })
  const transactionActions = useTransactionActions({ ...accountDetailState, ...accountForms, ...accountDetailData })
  const investmentActions = useInvestmentActions({ ...accountDetailState, ...accountForms, ...accountDetailData, ...transactionActions })
  const transactionView = useTransactionView({ ...accountDetailState, ...accountForms, ...accountDetailData, ...transactionActions, ...investmentActions })
  return { ...accountDetailState, ...accountForms, ...accountDetailData, ...transactionActions, ...investmentActions, ...transactionView }
}

export type AccountDetailCtx = ReturnType<typeof useAccountDetail>
/** Contexte passé aux sections, une fois le compte chargé (non nul). */
export type AccountDetailView = AccountDetailCtx & { account: Account; isInvestment: boolean; currentBalance: number }
