import { act, renderHook } from "@testing-library/react"
import { useSubmit } from "./useSubmit"

/** Promesse contrôlée de l'extérieur, pour observer l'état pendant l'exécution. */
function deferred() {
  let resolve!: () => void
  let reject!: (error: Error) => void
  const promise = new Promise<void>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe("useSubmit", () => {
  it("ignore un second appel pendant l'exécution du premier", async () => {
    const pending = deferred()
    const action = vi.fn((_label: string) => pending.promise)
    const { result } = renderHook(() => useSubmit(action))

    let first!: Promise<void>
    act(() => {
      first = result.current[0]("a")
      void result.current[0]("b")
    })

    expect(action).toHaveBeenCalledTimes(1)
    expect(action).toHaveBeenCalledWith("a")
    expect(result.current[1]).toBe(true)

    await act(async () => {
      pending.resolve()
      await first
    })
    expect(result.current[1]).toBe(false)
  })

  it("accepte un nouvel appel une fois le premier terminé", async () => {
    const action = vi.fn(() => Promise.resolve())
    const { result } = renderHook(() => useSubmit(action))

    await act(() => result.current[0]())
    await act(() => result.current[0]())

    expect(action).toHaveBeenCalledTimes(2)
  })

  it("repasse busy à false et relâche le verrou après une erreur", async () => {
    const pending = deferred()
    const action = vi.fn(() => pending.promise)
    const { result } = renderHook(() => useSubmit(action))

    let call!: Promise<void>
    act(() => {
      call = result.current[0]()
    })
    expect(result.current[1]).toBe(true)

    await act(async () => {
      pending.reject(new Error("échec réseau"))
      await expect(call).rejects.toThrow("échec réseau")
    })
    expect(result.current[1]).toBe(false)

    action.mockImplementationOnce(() => Promise.resolve())
    await act(() => result.current[0]())
    expect(action).toHaveBeenCalledTimes(2)
  })

  it("appelle la dernière version de l'action sans changer de fonction protégée", async () => {
    const first = vi.fn(() => Promise.resolve())
    const second = vi.fn(() => Promise.resolve())
    const { result, rerender } = renderHook(({ action }) => useSubmit(action), { initialProps: { action: first } })
    const guarded = result.current[0]

    rerender({ action: second })
    await act(() => result.current[0]())

    expect(result.current[0]).toBe(guarded)
    expect(first).not.toHaveBeenCalled()
    expect(second).toHaveBeenCalledTimes(1)
  })
})
