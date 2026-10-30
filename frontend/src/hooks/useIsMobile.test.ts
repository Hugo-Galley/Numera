import { act, renderHook } from "@testing-library/react"
import { useIsMobile } from "./useIsMobile"

/** `matchMedia` simulé : `matches` réglable, écouteurs `change` déclenchables. */
function mockMatchMedia(initial: boolean) {
  const listeners = new Set<() => void>()
  const mql = {
    matches: initial,
    media: "",
    addEventListener: (_: string, cb: () => void) => listeners.add(cb),
    removeEventListener: (_: string, cb: () => void) => listeners.delete(cb),
  }
  const spy = vi.spyOn(window, "matchMedia").mockImplementation((query: string) => {
    mql.media = query
    return mql as unknown as MediaQueryList
  })
  const change = (matches: boolean) => {
    mql.matches = matches
    listeners.forEach((cb) => cb())
  }
  return { spy, listeners, change }
}

describe("useIsMobile", () => {
  it("interroge le breakpoint md (max-width: 767px)", () => {
    const { spy } = mockMatchMedia(false)
    renderHook(() => useIsMobile())
    expect(spy).toHaveBeenCalledWith("(max-width: 767px)")
  })

  it("renvoie la valeur initiale de la media query", () => {
    mockMatchMedia(true)
    expect(renderHook(() => useIsMobile()).result.current).toBe(true)
  })

  it("suit les changements de largeur", () => {
    const { change } = mockMatchMedia(false)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)

    act(() => change(true))
    expect(result.current).toBe(true)

    act(() => change(false))
    expect(result.current).toBe(false)
  })

  it("retire son écouteur au démontage", () => {
    const { listeners } = mockMatchMedia(false)
    const { unmount } = renderHook(() => useIsMobile())
    expect(listeners.size).toBe(1)
    unmount()
    expect(listeners.size).toBe(0)
  })
})
