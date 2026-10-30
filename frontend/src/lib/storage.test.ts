import { safeStorage } from "./storage"

describe("safeStorage", () => {
  it("lit et écrit dans localStorage quand il est disponible", () => {
    safeStorage.setItem("theme", "dark")
    expect(window.localStorage.getItem("theme")).toBe("dark")
    expect(safeStorage.getItem("theme")).toBe("dark")
    safeStorage.removeItem("theme")
    expect(window.localStorage.getItem("theme")).toBeNull()
    expect(safeStorage.getItem("absent")).toBeNull()
  })

  describe("quand localStorage jette (navigation privée, données bloquées)", () => {
    beforeEach(() => {
      const fail = () => {
        throw new DOMException("bloqué", "SecurityError")
      }
      vi.spyOn(Storage.prototype, "getItem").mockImplementation(fail)
      vi.spyOn(Storage.prototype, "setItem").mockImplementation(fail)
      vi.spyOn(Storage.prototype, "removeItem").mockImplementation(fail)
    })

    it("ne lève jamais", () => {
      expect(() => safeStorage.setItem("k", "v")).not.toThrow()
      expect(() => safeStorage.getItem("k")).not.toThrow()
      expect(() => safeStorage.removeItem("k")).not.toThrow()
    })

    it("garde les valeurs en mémoire le temps de l'onglet", () => {
      safeStorage.setItem("privacy", "on")
      expect(safeStorage.getItem("privacy")).toBe("on")
      safeStorage.removeItem("privacy")
      expect(safeStorage.getItem("privacy")).toBeNull()
    })
  })

  it("ne lève pas si localStorage est absent", () => {
    const spy = vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("absent", "SecurityError")
    })
    try {
      expect(() => safeStorage.setItem("k", "v")).not.toThrow()
      expect(safeStorage.getItem("k")).toBe("v")
      safeStorage.removeItem("k")
      expect(safeStorage.getItem("k")).toBeNull()
    } finally {
      // rendu avant l'afterEach du setup, qui vide localStorage
      spy.mockRestore()
    }
  })
})
