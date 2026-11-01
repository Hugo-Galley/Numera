// Garde-fou ESLint à cliquet : les erreurs échouent toujours ; les avertissements existants
// sont plafonnés par fichier et par règle dans eslint-baseline.json (ne peut que diminuer).
//   node scripts/check-lint.mjs                   # contrôle (code 1 si dépassement)
//   node scripts/check-lint.mjs --write-baseline  # régénère la baseline (à ne faire que pour la diminuer)
import { spawnSync } from "node:child_process"
import { readFileSync, writeFileSync } from "node:fs"
import { dirname, relative, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const baselinePath = resolve(root, "eslint-baseline.json")

const run = spawnSync("npx", ["eslint", ".", "-f", "json"], { cwd: root, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 })
let results
try {
  results = JSON.parse(run.stdout)
} catch {
  console.error(run.stderr || run.stdout)
  process.exit(2)
}

const warnings = {}
let errors = 0
for (const file of results) {
  const rel = relative(root, file.filePath)
  for (const m of file.messages) {
    if (m.severity === 2) {
      errors++
      console.error(`${rel}:${m.line} ${m.ruleId ?? ""} ${m.message}`)
    } else {
      const key = `${rel}::${m.ruleId}`
      warnings[key] = (warnings[key] ?? 0) + 1
    }
  }
}

if (process.argv.includes("--write-baseline")) {
  const sorted = Object.fromEntries(Object.entries(warnings).sort(([a], [b]) => a.localeCompare(b)))
  writeFileSync(baselinePath, JSON.stringify(sorted, null, 2) + "\n")
  console.log(`Baseline écrite : ${Object.values(sorted).reduce((a, b) => a + b, 0)} avertissements dans ${Object.keys(sorted).length} entrées.`)
  process.exit(errors ? 1 : 0)
}

const baseline = JSON.parse(readFileSync(baselinePath, "utf8"))
const problems = []
for (const [key, count] of Object.entries(warnings)) {
  if (count > (baseline[key] ?? 0)) problems.push(`${key} : ${count} avertissements (autorisé : ${baseline[key] ?? 0})`)
}
for (const [key, allowed] of Object.entries(baseline)) {
  if ((warnings[key] ?? 0) < allowed) problems.push(`${key} : baseline obsolète (${allowed} → ${warnings[key] ?? 0}), relancer avec --write-baseline`)
}
if (errors || problems.length) {
  console.error(problems.join("\n"))
  process.exit(1)
}
console.log(`ESLint OK (${Object.values(warnings).reduce((a, b) => a + b, 0)} avertissements tolérés par la baseline, 0 erreur)`)
