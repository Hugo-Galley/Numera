import { waitFor } from "@testing-library/react"
import { startPrivacyScanner } from "./privacyScanner"

// Détection de texte (`looksSensitive`) : voir privacyScanner.test.ts. Ici, le scanner DOM.
const MASK = "privacy-masked"
let stop: (() => void) | null = null

function add(html: string): HTMLElement {
  const host = document.createElement("div")
  host.innerHTML = html
  document.body.appendChild(host)
  return host
}

/** Laisse passer une frame d'animation (le scanner regroupe les mutations par frame). */
const nextFrame = () => new Promise((resolve) => requestAnimationFrame(resolve))

afterEach(() => {
  stop?.()
  stop = null
  document.body.innerHTML = ""
})

describe("startPrivacyScanner", () => {
  it("masque les montants déjà présents au démarrage, pas le reste", () => {
    const host = add(`<p id="amount">1 234,56 €</p><p id="label">Courses</p>`)
    stop = startPrivacyScanner()

    expect(host.querySelector("#amount")).toHaveClass(MASK)
    expect(host.querySelector("#label")).not.toHaveClass(MASK)
  })

  it("ne masque que l'élément qui porte le texte, pas son conteneur", () => {
    const host = add(`<section id="card"><h2>Solde</h2><span id="value">2 500 €</span></section>`)
    stop = startPrivacyScanner()

    expect(host.querySelector("#value")).toHaveClass(MASK)
    expect(host.querySelector("#card")).not.toHaveClass(MASK)
  })

  it("masque un montant inséré après coup (MutationObserver)", async () => {
    const host = add(`<ul id="list"></ul>`)
    stop = startPrivacyScanner()

    const item = document.createElement("li")
    item.textContent = "Loyer 850,00 €"
    host.querySelector("#list")!.appendChild(item)

    await waitFor(() => expect(item).toHaveClass(MASK))
  })

  it("réévalue un texte modifié : masque puis démasque", async () => {
    const host = add(`<span id="v">—</span>`)
    stop = startPrivacyScanner()
    const span = host.querySelector("#v")!
    expect(span).not.toHaveClass(MASK)

    span.firstChild!.nodeValue = "42 €"
    await waitFor(() => expect(span).toHaveClass(MASK))

    span.textContent = "aucune donnée"
    await waitFor(() => expect(span).not.toHaveClass(MASK))
  })

  it("respecte data-privacy-ignore, au démarrage comme après insertion", async () => {
    const host = add(`<div data-privacy-ignore><p id="before">1 000 €</p></div>`)
    stop = startPrivacyScanner()
    expect(host.querySelector("#before")).not.toHaveClass(MASK)

    const late = document.createElement("p")
    late.textContent = "2 000 €"
    host.querySelector("[data-privacy-ignore]")!.appendChild(late)
    await nextFrame()
    await nextFrame()

    expect(late).not.toHaveClass(MASK)
  })

  it("masque un champ number et un champ texte contenant un montant", async () => {
    const host = add(`<input id="n" type="number" value="" /><input id="t" type="text" value="" />`)
    stop = startPrivacyScanner()
    const text = host.querySelector<HTMLInputElement>("#t")!

    expect(host.querySelector("#n")).toHaveClass(MASK)
    expect(text).not.toHaveClass(MASK)

    text.value = "1 250,00"
    text.dispatchEvent(new Event("input", { bubbles: true }))
    expect(text).toHaveClass(MASK)
  })

  it("SVG : masque le <text> parent d'un <tspan> qui contient un montant", () => {
    const host = add(`<svg><text id="axis"><tspan>12 k€</tspan></text><text id="month"><tspan>Juin</tspan></text></svg>`)
    stop = startPrivacyScanner()

    expect(host.querySelector("#axis")).toHaveClass(MASK)
    expect(host.querySelector("tspan")).not.toHaveClass(MASK)
    expect(host.querySelector("#month")).not.toHaveClass(MASK)
  })

  it("l'arrêt retire tous les masques et cesse d'observer", async () => {
    const host = add(`<p id="a">10 €</p><p id="b">20 €</p>`)
    const cleanup = startPrivacyScanner()
    expect(host.querySelectorAll(`.${MASK}`)).toHaveLength(2)

    cleanup()
    expect(host.querySelectorAll(`.${MASK}`)).toHaveLength(0)

    const late = document.createElement("p")
    late.textContent = "30 €"
    host.appendChild(late)
    await nextFrame()
    await nextFrame()
    expect(late).not.toHaveClass(MASK)
  })

  it("l'arrêt annule une analyse en attente", async () => {
    const host = add(`<div id="zone"></div>`)
    const cleanup = startPrivacyScanner()
    const late = document.createElement("p")
    late.textContent = "99 €"
    host.querySelector("#zone")!.appendChild(late)

    cleanup()
    await nextFrame()
    await nextFrame()

    expect(late).not.toHaveClass(MASK)
  })
})
