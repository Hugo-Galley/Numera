/**
 * Mode confidentialité : détection automatique des montants affichés.
 *
 * Plutôt que de dépendre de la classe `amount-blur` posée à la main, on observe
 * le DOM et on marque (`privacy-masked`) tout élément dont un texte direct ressemble
 * à un montant : devise, séparateurs de milliers, décimales. Couvre aussi les textes
 * SVG des graphiques, les infobulles Recharts et les champs de saisie.
 * Les nœuds texte ne sont jamais modifiés (React en reste propriétaire) : seule une
 * classe est ajoutée sur l'élément parent.
 */

const MASK_CLASS = "privacy-masked"
const IGNORE_SELECTOR = "[data-privacy-ignore], script, style, noscript, title"

const CURRENCY = "(?:€|\\$|£|¥|EUR|USD|GBP|CHF)"
const AMOUNT_PATTERNS: RegExp[] = [
  // 1 234,56 € · 12 € · $ 45 · 3k€
  new RegExp(`\\d\\s*[kKM]?\\s*${CURRENCY}`),
  new RegExp(`${CURRENCY}\\s*\\d`),
  // 1 234,56 · 1.234,56 · 1 234 (séparateurs de milliers), en début de nombre : pas « 10.202 » dans 22.10.2026
  /(?<![\d.,])\d{1,3}(?:[\s  .,]\d{3})+(?:[.,]\d+)?(?!\d)/,
  // 12,50 · 12.50 (décimales de montant), hors date/version type 22.10.2026 et pourcentage (3,14 %)
  /(?<![\d.,])\d+[.,]\d{2}(?![\d.,])(?!\s*%)/,
]

export function looksSensitive(text: string | null | undefined): boolean {
  if (!text || text.length > 200 || !/\d/.test(text)) return false
  return AMOUNT_PATTERNS.some((re) => re.test(text))
}

function maskTarget(el: Element): Element {
  // Les <tspan>/<title> SVG n'acceptent pas `filter` : on remonte au <text>.
  if (el instanceof SVGElement) return el.closest("text") ?? el
  return el
}

function evaluateElement(el: Element | null) {
  if (!el || el === document.body || el.closest(IGNORE_SELECTOR)) return
  const target = maskTarget(el)

  let sensitive = false
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
    sensitive = target.type === "number" || looksSensitive(target.value)
  } else {
    // Texte du <text>/de l'élément lui-même (SVG : tspans inclus)
    const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT)
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const owner = n.parentElement
      // en HTML on ne regarde que les textes directs, pour ne pas masquer un conteneur entier
      if (target instanceof SVGElement || owner === target) {
        if (looksSensitive(n.nodeValue)) {
          sensitive = true
          break
        }
      }
    }
  }

  if (sensitive) target.classList.add(MASK_CLASS)
  else target.classList.remove(MASK_CLASS)
}

function scanSubtree(root: Node) {
  if (root.nodeType === Node.TEXT_NODE) {
    evaluateElement(root.parentElement)
    return
  }
  if (!(root instanceof Element)) return
  evaluateElement(root)
  root.querySelectorAll("*").forEach((el) => evaluateElement(el))
}

export function startPrivacyScanner(): () => void {
  const pending = new Set<Node>()
  let frame = 0

  const flush = () => {
    frame = 0
    pending.forEach((n) => {
      if (n.isConnected) scanSubtree(n)
    })
    pending.clear()
  }
  const schedule = (n: Node) => {
    pending.add(n)
    if (!frame) frame = requestAnimationFrame(flush)
  }

  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === "characterData") {
        if (m.target.parentElement) schedule(m.target.parentElement)
      } else if (m.type === "childList") {
        m.addedNodes.forEach(schedule)
        // un texte remplacé : réévaluer le parent
        if (m.target instanceof Element) schedule(m.target)
      } else if (m.type === "attributes" && m.target instanceof Element) {
        schedule(m.target)
      }
    }
  })

  const onInput = (e: Event) => {
    if (e.target instanceof Element) evaluateElement(e.target)
  }

  observer.observe(document.body, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ["value"],
  })
  document.addEventListener("input", onInput, true)
  scanSubtree(document.body)

  return () => {
    observer.disconnect()
    document.removeEventListener("input", onInput, true)
    if (frame) cancelAnimationFrame(frame)
    document.querySelectorAll(`.${MASK_CLASS}`).forEach((el) => el.classList.remove(MASK_CLASS))
  }
}
