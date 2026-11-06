/** Garde-fou : un format de date ou de montant écrit en dur ignorerait la langue choisie dans Paramètres. */
const sources = import.meta.glob<string>("/src/**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true })

const FORBIDDEN = [
  { pattern: /["'`]fr-FR["'`]/, advice: "utiliser appLocale() de @/i18n/locale" },
  { pattern: /locale[:=]\s*\{?\s*fr\b/, advice: "utiliser dateLocale() de @/i18n/locale" },
  { pattern: /from "date-fns\/locale\/fr"/, advice: "utiliser dateLocale() de @/i18n/locale" },
]

describe("formats liés à la langue", () => {
  it("aucune locale française écrite en dur hors de src/i18n", () => {
    const offenders: string[] = []
    for (const [path, code] of Object.entries(sources)) {
      if (path.startsWith("/src/i18n/") || path.startsWith("/src/test/") || /\.test\.tsx?$/.test(path)) continue
      for (const { pattern, advice } of FORBIDDEN) {
        if (pattern.test(code)) offenders.push(`${path} : ${advice}`)
      }
    }
    expect(offenders).toEqual([])
  })
})
