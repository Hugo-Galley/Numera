import { LANGUAGES, resources } from "@/i18n/index"

type Tree = { [key: string]: string | Tree }

function keys(tree: Tree, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string" ? [`${prefix}${key}`] : keys(value, `${prefix}${key}.`),
  )
}

const placeholders = (text: string) => (text.match(/{{\s*\w+\s*}}/g) ?? []).map((p) => p.replace(/\s/g, "")).sort()

function lookup(tree: Tree, path: string): string {
  return path.split(".").reduce<string | Tree>((node, key) => (node as Tree)[key], tree) as string
}

describe("catalogues de traduction", () => {
  for (const namespace of Object.keys(resources.fr) as (keyof typeof resources.fr)[]) {
    describe(namespace, () => {
      const fr = resources.fr[namespace] as Tree

      for (const language of LANGUAGES.filter((code) => code !== "fr")) {
        const other = resources[language][namespace] as Tree

        it(`${language} a exactement les clés du français`, () => {
          expect(keys(other).sort()).toEqual(keys(fr).sort())
        })

        it(`${language} : chaque clé a un texte non vide et les mêmes variables {{…}} qu'en français`, () => {
          for (const key of keys(fr)) {
            expect(lookup(fr, key).trim(), `fr ${namespace}.${key}`).not.toBe("")
            expect(lookup(other, key).trim(), `${language} ${namespace}.${key}`).not.toBe("")
            expect(placeholders(lookup(other, key)), `variables de ${namespace}.${key}`).toEqual(placeholders(lookup(fr, key)))
          }
        })
      }
    })
  }
})
