import { useSimulatorState } from "./useSimulatorState"
import { useSimulatorActions } from "./useSimulatorActions"

/** Assemble l'état, les chargements et les actions de WealthSimulator. */
export function useWealthSimulator(initialCapitalDefault: number) {
  const simulatorState = useSimulatorState({ initialCapitalDefault })
  const simulatorActions = useSimulatorActions({ initialCapitalDefault, ...simulatorState })
  return { initialCapitalDefault, ...simulatorState, ...simulatorActions }
}

export type WealthSimulatorCtx = ReturnType<typeof useWealthSimulator>
