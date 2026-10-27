// Génère src/theme-colors.css (palettes Tailwind en variables CSS, inversées en sombre).
// Usage : node scripts/gen-theme-colors.cjs (depuis frontend/)
const path = require("path")
const root = path.resolve(__dirname, "..")
const colors = require(path.join(root, "node_modules/tailwindcss/colors"))
const fs = require("fs")

const hex = (h) => {
  h = h.replace("#", "")
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)).join(" ")
}
const shades = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"]
const palettes = ["slate", "gray", "red", "orange", "amber", "yellow", "lime", "green", "emerald", "teal", "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink", "rose"]
const slateDark = {
  50: "#020617", 100: "#1e293b", 200: "#283548", 300: "#475569", 400: "#8696ab", 500: "#94a3b8",
  600: "#cbd5e1", 700: "#e2e8f0", 800: "#f1f5f9", 900: "#f8fafc", 950: "#ffffff",
}

let light = ""
let dark = ""
for (const p of palettes) {
  for (const s of shades) {
    light += `    --c-${p}-${s}: ${hex(colors[p][s])};\n`
    const d = p === "slate" ? slateDark[s] : colors[p][shades[shades.length - 1 - shades.indexOf(s)]]
    dark += `    --c-${p}-${s}: ${hex(d)};\n`
  }
}
light += "    --c-white: 255 255 255;\n"
dark += `    --c-white: ${hex("#0f172a")};\n`

const css = `/* Généré par scripts/gen-theme-colors.cjs : palettes Tailwind en variables CSS (cf. tailwind.config.js).
   En sombre (.dark), chaque échelle est inversée (50 <-> 950, 100 <-> 900…) et l'ardoise est ajustée :
   bg-white, text-slate-900, bg-emerald-50… basculent seules. Ne pas ajouter de variantes dark: sur ces couleurs.
   .theme-island : îlot volontairement sombre (carte héros bg-slate-900 text-white, story Wrapped…) qui garde
   la palette claire en sombre, sinon il deviendrait blanc avec un texte secondaire illisible. */
:root,
.dark .theme-island {
${light}}

.dark {
${dark}}
`
fs.writeFileSync(path.join(root, "src/theme-colors.css"), css)
