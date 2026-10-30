import { act, fireEvent, screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/render"
import { useUI, type ThemePreference } from "./UIProvider"

function Controls() {
  const { theme, setTheme, isPrivacyMode, togglePrivacyMode, hideHoldingValues, setHideHoldingValues, isSearchOpen } = useUI()
  return (
    <div>
      <p>thème : {theme}</p>
      <p>confidentialité : {isPrivacyMode ? "oui" : "non"}</p>
      <p>valeurs titres : {hideHoldingValues ? "masquées" : "visibles"}</p>
      <p>recherche : {isSearchOpen ? "ouverte" : "fermée"}</p>
      {(["light", "dark", "system"] as ThemePreference[]).map((t) => (
        <button key={t} onClick={() => setTheme(t)}>
          {t}
        </button>
      ))}
      <button onClick={togglePrivacyMode}>Œil</button>
      <button onClick={() => setHideHoldingValues(!hideHoldingValues)}>Titres</button>
    </div>
  )
}

/** `prefers-color-scheme` simulé, avec bascule du thème système. */
function mockSystemDark(initial: boolean) {
  // le Toaster (sonner) écoute aussi cette media query et lit `event.matches`
  const listeners = new Set<(event: { matches: boolean }) => void>()
  const mql = {
    matches: initial,
    addEventListener: (_: string, cb: (event: { matches: boolean }) => void) => listeners.add(cb),
    removeEventListener: (_: string, cb: (event: { matches: boolean }) => void) => listeners.delete(cb),
  }
  vi.spyOn(window, "matchMedia").mockImplementation(() => mql as unknown as MediaQueryList)
  return {
    change(dark: boolean) {
      mql.matches = dark
      listeners.forEach((cb) => cb({ matches: dark }))
    },
  }
}

const html = document.documentElement
const stored = (key: string) => window.localStorage.getItem(key)

afterEach(() => {
  html.classList.remove("dark")
  document.body.classList.remove("privacy-enabled")
})

describe("UIProvider : thème", () => {
  it("par défaut « system » : suit le système et le persiste", () => {
    mockSystemDark(true)
    renderWithProviders(<Controls />)

    expect(screen.getByText("thème : system")).toBeInTheDocument()
    expect(html).toHaveClass("dark")
    expect(stored("theme")).toBe("system")
  })

  it("reprend le thème enregistré", () => {
    window.localStorage.setItem("theme", "dark")
    renderWithProviders(<Controls />)
    expect(screen.getByText("thème : dark")).toBeInTheDocument()
    expect(html).toHaveClass("dark")
  })

  it("une valeur enregistrée inconnue retombe sur « system »", () => {
    window.localStorage.setItem("theme", "violet")
    mockSystemDark(false)
    renderWithProviders(<Controls />)
    expect(screen.getByText("thème : system")).toBeInTheDocument()
    expect(stored("theme")).toBe("system")
  })

  it("light / dark posent ou retirent la classe dark et la persistent, quel que soit le système", async () => {
    mockSystemDark(true)
    const { user } = renderWithProviders(<Controls />)

    await user.click(screen.getByRole("button", { name: "light" }))
    expect(html).not.toHaveClass("dark")
    expect(stored("theme")).toBe("light")

    await user.click(screen.getByRole("button", { name: "dark" }))
    expect(html).toHaveClass("dark")
    expect(stored("theme")).toBe("dark")
  })

  it("en « system », suit un changement du thème du système ; plus après un choix explicite", async () => {
    const media = mockSystemDark(false)
    const { user } = renderWithProviders(<Controls />)
    expect(html).not.toHaveClass("dark")

    act(() => media.change(true))
    expect(html).toHaveClass("dark")

    await user.click(screen.getByRole("button", { name: "light" }))
    act(() => media.change(true))
    expect(html).not.toHaveClass("dark")
  })

  it("met à jour la meta theme-color", async () => {
    const meta = document.createElement("meta")
    meta.name = "theme-color"
    document.head.appendChild(meta)
    try {
      window.localStorage.setItem("theme", "dark")
      const { user } = renderWithProviders(<Controls />)
      expect(meta.content).toBe("#020617")
      await user.click(screen.getByRole("button", { name: "light" }))
      expect(meta.content).toBe("#0f172a")
    } finally {
      meta.remove()
    }
  })
})

describe("UIProvider : mode confidentialité", () => {
  it("désactivé par défaut", () => {
    renderWithProviders(<Controls />)
    expect(screen.getByText("confidentialité : non")).toBeInTheDocument()
    expect(document.body).not.toHaveClass("privacy-enabled")
    expect(stored("privacy-mode")).toBe("false")
  })

  it("la bascule pose privacy-enabled sur <body> et la persiste, puis l'enlève", async () => {
    const { user } = renderWithProviders(<Controls />)

    await user.click(screen.getByRole("button", { name: "Œil" }))
    expect(screen.getByText("confidentialité : oui")).toBeInTheDocument()
    expect(document.body).toHaveClass("privacy-enabled")
    expect(stored("privacy-mode")).toBe("true")

    await user.click(screen.getByRole("button", { name: "Œil" }))
    expect(document.body).not.toHaveClass("privacy-enabled")
    expect(stored("privacy-mode")).toBe("false")
  })

  it("reprend l'état enregistré et lance le scanner de montants", () => {
    window.localStorage.setItem("privacy-mode", "true")
    renderWithProviders(<p>Solde : 1 234,56 €</p>)

    expect(document.body).toHaveClass("privacy-enabled")
    expect(screen.getByText("Solde : 1 234,56 €")).toHaveClass("privacy-masked")
  })

  it("en quittant le mode, le masquage des montants est retiré", async () => {
    window.localStorage.setItem("privacy-mode", "true")
    const { user } = renderWithProviders(
      <>
        <Controls />
        <p>Solde : 1 234,56 €</p>
      </>,
    )
    expect(screen.getByText("Solde : 1 234,56 €")).toHaveClass("privacy-masked")

    await user.click(screen.getByRole("button", { name: "Œil" }))
    expect(screen.getByText("Solde : 1 234,56 €")).not.toHaveClass("privacy-masked")
  })
})

describe("UIProvider : autres préférences", () => {
  it("valeurs des titres masquées : persistance et lecture au démarrage", async () => {
    const { user, unmount } = renderWithProviders(<Controls />)
    expect(stored("hide-holding-values")).toBe("false")

    await user.click(screen.getByRole("button", { name: "Titres" }))
    expect(stored("hide-holding-values")).toBe("true")

    unmount()
    renderWithProviders(<Controls />)
    expect(screen.getByText("valeurs titres : masquées")).toBeInTheDocument()
  })

  it.each([{ metaKey: true }, { ctrlKey: true }])("⌘K / Ctrl+K ouvre puis ferme la recherche (%o)", (modifier) => {
    renderWithProviders(<Controls />)

    fireEvent.keyDown(document, { key: "k", ...modifier })
    expect(screen.getByText("recherche : ouverte")).toBeInTheDocument()

    fireEvent.keyDown(document, { key: "k", ...modifier })
    expect(screen.getByText("recherche : fermée")).toBeInTheDocument()
  })

  it("« k » seul n'ouvre pas la recherche", () => {
    renderWithProviders(<Controls />)
    fireEvent.keyDown(document, { key: "k" })
    expect(screen.getByText("recherche : fermée")).toBeInTheDocument()
  })
})
