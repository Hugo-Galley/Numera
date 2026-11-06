import { resources } from "./index"

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
      const en = resources.en[namespace] as Tree

      it("l'anglais a exactement les clés du français", () => {
        expect(keys(en).sort()).toEqual(keys(fr).sort())
      })

      it("chaque clé a un texte non vide et les mêmes variables {{…}} dans les deux langues", () => {
        for (const key of keys(fr)) {
          expect(lookup(fr, key).trim(), `fr ${namespace}.${key}`).not.toBe("")
          expect(lookup(en, key).trim(), `en ${namespace}.${key}`).not.toBe("")
          expect(placeholders(lookup(en, key)), `variables de ${namespace}.${key}`).toEqual(placeholders(lookup(fr, key)))
        }
      })
    })
  }
})
