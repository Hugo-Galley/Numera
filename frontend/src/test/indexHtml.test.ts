/** index.html : la CSP de production (`script-src 'self'`, frontend/nginx.conf) bloque tout script inline. */
import { readFileSync } from "node:fs"
import { resolve } from "node:path"

const html = readFileSync(resolve(__dirname, "../../index.html"), "utf8")
const nginx = readFileSync(resolve(__dirname, "../../nginx.conf"), "utf8")

describe("index.html et Content-Security-Policy", () => {
  it("la production n'autorise que les scripts servis par le site", () => {
    expect(nginx).toContain("script-src 'self';")
    expect(nginx).not.toMatch(/script-src[^;]*'unsafe-inline'/)
  })

  it("aucun script inline : chaque <script> charge un fichier", () => {
    const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)]
    expect(scripts.length).toBeGreaterThan(0)
    for (const [, attrs, body] of scripts) {
      expect(attrs).toMatch(/\bsrc=/)
      expect(body.trim()).toBe("")
    }
  })

  it("le thème est posé avant React par un script bloquant du dossier public", () => {
    const head = html.slice(0, html.indexOf("</head>"))
    expect(head).toMatch(/<script src="\/theme-init\.js"><\/script>/)
    const init = readFileSync(resolve(__dirname, "../../public/theme-init.js"), "utf8")
    expect(init).toContain('classList.toggle("dark"')
  })
})
