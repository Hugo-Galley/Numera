/** Serveur MSW (mode Node) partagé par tous les tests ; surcharger une réponse avec `server.use(...)`. */
import { setupServer } from "msw/node"
import { handlers } from "./handlers"

export const server = setupServer(...handlers)
