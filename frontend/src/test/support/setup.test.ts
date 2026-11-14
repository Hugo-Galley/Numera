/** Garde-fous de `setup.ts` : le nettoyage entre deux tests ne doit pas produire d'échec intermittent. */
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"

describe("setup : requêtes encore en vol à la fin d'un test", () => {
  // Un composant qui lance une requête juste avant la fin du test (useEffect au montage) : si `afterEach`
  // réinitialise les handlers avant que MSW l'ait appariée, elle part « sans handler » et le test échoue au hasard.
  it("une requête lancée sans être attendue trouve quand même son handler", () => {
    server.use(http.get(apiUrl("/en-vol"), () => HttpResponse.json({ ok: true })))
    // Différée d'un tour, comme un `api.get` qui passe par le cache de requêtes avant d'appeler `fetch`
    setTimeout(() => void fetch(apiUrl("/en-vol")), 0)
  })

  // Une requête appariée trop tard est enregistrée pendant le test suivant, qui échoue à sa place : ce test-ci
  // laisse passer un tour de boucle pour la voir arriver.
  it("le test suivant n'hérite pas d'une requête « sans handler » du précédent", async () => {
    await new Promise((resolve) => setTimeout(resolve, 50))
  })
})
