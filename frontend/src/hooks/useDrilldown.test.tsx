import type { ReactNode } from "react"
import { act, renderHook } from "@testing-library/react"
import { MemoryRouter, useLocation } from "react-router-dom"
import { readDrilldown, useDrilldown } from "./useDrilldown"

function setup(route: string) {
  const wrapper = ({ children }: { children: ReactNode }) => <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
  const { result } = renderHook(() => ({ ...useDrilldown(), location: useLocation() }), { wrapper })
  const params = () => new URLSearchParams(result.current.location.search)
  return { result, params }
}

describe("useDrilldown", () => {
  it("openDrilldown écrit les paramètres dd_* sans toucher aux autres", () => {
    const { result, params } = setup("/analytics?tab=budget&month=6")

    act(() =>
      result.current.openDrilldown({ label: "Courses", month: 6, year: 2026, categoryId: 4, merchantName: "Carrefour", accountId: 2 }),
    )

    expect(result.current.location.pathname).toBe("/analytics")
    expect(Object.fromEntries(params())).toEqual({
      tab: "budget",
      month: "6",
      dd_label: "Courses",
      dd_m: "6",
      dd_y: "2026",
      dd_cat: "4",
      dd_merchant: "Carrefour",
      dd_acc: "2",
    })
  })

  it("encode « Sans catégorie » (null) en dd_cat=none et omet les filtres absents", () => {
    const { result, params } = setup("/")

    act(() => result.current.openDrilldown({ label: "Sans catégorie", month: 1, year: 2026, categoryId: null, accountId: null }))

    expect(params().get("dd_cat")).toBe("none")
    expect(params().has("dd_merchant")).toBe(false)
    expect(params().has("dd_acc")).toBe(false)
    expect(readDrilldown(params())).toEqual({
      label: "Sans catégorie",
      month: 1,
      year: 2026,
      categoryId: null,
      merchantName: undefined,
      accountId: null,
    })
  })

  it("une nouvelle ouverture remplace les filtres précédents", () => {
    const { result, params } = setup("/?dd_label=Ancien&dd_m=1&dd_y=2025&dd_merchant=Amazon&dd_cat=3")

    act(() => result.current.openDrilldown({ label: "Loyer", month: 2, year: 2026 }))

    expect(Object.fromEntries(params())).toEqual({ dd_label: "Loyer", dd_m: "2", dd_y: "2026" })
  })

  it("closeDrilldown retire les dd_* et garde les autres paramètres", () => {
    const { result, params } = setup("/accounts/1?tab=tx&dd_label=Courses&dd_m=6&dd_y=2026&dd_cat=none&dd_merchant=X&dd_acc=1")

    act(() => result.current.closeDrilldown())

    expect(result.current.location.pathname).toBe("/accounts/1")
    expect(params().toString()).toBe("tab=tx")
  })
})

describe("readDrilldown", () => {
  it("renvoie null sans libellé, mois ou année", () => {
    expect(readDrilldown(new URLSearchParams("dd_m=6&dd_y=2026"))).toBeNull()
    expect(readDrilldown(new URLSearchParams("dd_label=X&dd_y=2026"))).toBeNull()
    expect(readDrilldown(new URLSearchParams("dd_label=X&dd_m=6"))).toBeNull()
  })

  it("laisse categoryId indéfini quand dd_cat est absent (toutes catégories)", () => {
    expect(readDrilldown(new URLSearchParams("dd_label=X&dd_m=6&dd_y=2026"))?.categoryId).toBeUndefined()
  })
})
