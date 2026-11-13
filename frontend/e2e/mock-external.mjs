// Faux services externes des E2E « sécurité » (port 8103), jamais de vrai réseau :
// - serveur ntfy : POST / enregistre le message et répond 200 ;
// - proxy HTTPS : tout CONNECT (api.telegram.org, Frankfurter…) est journalisé puis refusé en 502 ;
// - GET /__requests renvoie le journal, DELETE /__requests le vide (les tests le lisent par HTTP).
import http from "node:http"

const log = []
const server = http.createServer((req, res) => {
  if (req.url === "/__requests") {
    if (req.method === "DELETE") log.length = 0
    res.setHeader("content-type", "application/json")
    res.end(JSON.stringify(req.method === "DELETE" ? [] : log))
    return
  }
  if (req.url === "/health") return void res.end("ok")
  let body = ""
  req.on("data", (chunk) => (body += chunk))
  req.on("end", () => {
    let json = null
    try { json = JSON.parse(body) } catch { /* corps non JSON */ }
    log.push({ kind: "http", method: req.method, path: req.url, auth: req.headers.authorization ?? null, body: json })
    res.setHeader("content-type", "application/json")
    res.end("{}")
  })
})
server.on("connect", (req, socket) => {
  log.push({ kind: "connect", target: req.url })
  socket.end("HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
})
server.listen(8103, "127.0.0.1")
