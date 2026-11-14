import { describe, expect, it } from "vitest"
import { numberFormatter, toNumber } from "@/lib/chartTooltip"

describe("toNumber", () => {
  it("garde un nombre, convertit une chaîne, prend le premier élément d'un tableau", () => {
    expect(toNumber(12.5)).toBe(12.5)
    expect(toNumber("42")).toBe(42)
    expect(toNumber([7, 9])).toBe(7)
  })

  it("renvoie 0 pour une valeur non numérique", () => {
    expect(toNumber(undefined)).toBe(0)
    expect(toNumber("abc")).toBe(0)
  })
})

describe("numberFormatter", () => {
  it("passe un nombre, le nom de série et l'entrée au formatter", () => {
    const fmt = numberFormatter((v, name, item) => [`${v * 2}`, `${name}:${String(item.payload?.k)}`])
    expect(fmt("21", "Solde", { payload: { k: "x" } })).toEqual(["42", "Solde:x"])
  })

  it("remplace un nom absent par une chaîne vide", () => {
    const fmt = numberFormatter((_v, name) => name)
    expect(fmt(1, undefined, {})).toBe("")
  })
})
