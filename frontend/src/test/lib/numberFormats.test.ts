/**
 * Garde-fou : un montant abrégé ou un pourcentage ne se compose pas à la main (« 45k€ », « ${v}% »),
 * il passe par `formatCompactCurrency` / `formatRate` (lib/utils.ts), pour un rendu identique partout
 * et propre à la langue (« 45 k€ », « 21,9 % » en français, « €45k », « 21.9% » en anglais).
 */
const sources = import.meta.glob<string>("/src/**/*.tsx", { query: "?raw", import: "default", eager: true })

/** « k€ » écrit en dur, ou nombre interpolé suivi de « % » dans un texte (pas une largeur CSS). */
const HAND_MADE = [/k€/, /\}%\s*</, /\} ?%`/, /\} ?€`/]

describe("formats de nombres", () => {
  it("le garde-fou lit bien les sources", () => {
    expect(Object.keys(sources).length).toBeGreaterThan(150)
  })

  it("aucun montant abrégé ni pourcentage composé à la main dans les écrans", () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => !path.startsWith("/src/test/"))
      .flatMap(([path, code]) =>
        code
          .split("\n")
          .map((line, i) => ({ line, at: `${path}:${i + 1}` }))
          .filter(({ line }) => HAND_MADE.some((re) => re.test(line)) && !/(width|height|left|top|translate)\s*:|translateX/.test(line))
          .map(({ at }) => at),
      )
    expect(offenders).toEqual([])
  })
})
