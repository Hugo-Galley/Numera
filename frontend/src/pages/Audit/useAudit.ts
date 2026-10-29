import { useActionCenterData } from "./useActionCenterData"

/** Assemble l'état, les chargements et les actions de Audit. */
export function useAudit() {
  const actionCenterData = useActionCenterData()
  return { ...actionCenterData }
}

export type AuditCtx = ReturnType<typeof useAudit>
