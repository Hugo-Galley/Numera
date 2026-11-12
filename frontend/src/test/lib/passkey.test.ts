/** WebAuthn : conversions base64url ↔ ArrayBuffer autour de navigator.credentials et connexion complète par passkey. */
import { http, HttpResponse } from "msw"
import { vi } from "vitest"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"
import { createCredential, getCredential, loginWithPasskey, passkeySupported, serializeCredential } from "@/lib/passkey"

const bytes = (...values: number[]) => Uint8Array.from(values).buffer
const asArray = (buffer: BufferSource) => Array.from(new Uint8Array(buffer as ArrayBuffer))

function stubCredentials(impl: { create?: (options: unknown) => Promise<unknown>; get?: (options: unknown) => Promise<unknown> } = {}) {
  const credentials = { create: vi.fn(impl.create ?? (async () => null)), get: vi.fn(impl.get ?? (async () => null)) }
  Object.defineProperty(navigator, "credentials", { value: credentials, configurable: true })
  return credentials
}

afterEach(() => {
  Reflect.deleteProperty(navigator, "credentials")
  vi.unstubAllGlobals()
})

describe("passkeySupported", () => {
  it("vrai seulement si le navigateur expose PublicKeyCredential et navigator.credentials", () => {
    vi.stubGlobal("PublicKeyCredential", undefined)
    stubCredentials()
    expect(passkeySupported()).toBe(false)

    vi.stubGlobal("PublicKeyCredential", class {})
    expect(passkeySupported()).toBe(true)

    Object.defineProperty(navigator, "credentials", { value: undefined, configurable: true })
    expect(passkeySupported()).toBe(false)
  })
})

describe("createCredential / getCredential", () => {
  it("création : le défi, l'identifiant utilisateur et les clés exclues passent de base64url à des tampons binaires", async () => {
    const credentials = stubCredentials({ create: async () => ({ id: "ok" }) })

    await createCredential({
      challenge: "AQID", // 0x01 0x02 0x03
      user: { id: "_-8", name: "admin" }, // octets 0xFF 0xEF (base64url sans remplissage)
      excludeCredentials: [{ id: "BAUG", type: "public-key" }],
      rp: { name: "Numera" },
    })

    const { publicKey } = credentials.create.mock.calls[0][0] as { publicKey: PublicKeyCredentialCreationOptions }
    expect(asArray(publicKey.challenge)).toEqual([1, 2, 3])
    expect(asArray(publicKey.user.id)).toEqual([255, 239])
    expect(publicKey.user.name).toBe("admin")
    expect(asArray(publicKey.excludeCredentials![0].id)).toEqual([4, 5, 6])
    expect(publicKey.rp).toEqual({ name: "Numera" })
  })

  it("création sans clés exclues : le champ reste absent", async () => {
    const credentials = stubCredentials({ create: async () => null })

    const result = await createCredential({ challenge: "AQID", user: { id: "AQID", name: "admin" } })

    expect(result).toBeNull()
    const { publicKey } = credentials.create.mock.calls[0][0] as { publicKey: PublicKeyCredentialCreationOptions }
    expect(publicKey.excludeCredentials).toBeUndefined()
  })

  it("connexion : le défi et les clés autorisées sont convertis", async () => {
    const credentials = stubCredentials({ get: async () => ({ id: "ok" }) })

    await getCredential({ challenge: "BwgJ", allowCredentials: [{ id: "AQID", type: "public-key" }], timeout: 60000 })

    const { publicKey } = credentials.get.mock.calls[0][0] as { publicKey: PublicKeyCredentialRequestOptions }
    expect(asArray(publicKey.challenge)).toEqual([7, 8, 9])
    expect(asArray(publicKey.allowCredentials![0].id)).toEqual([1, 2, 3])
    expect(publicKey.timeout).toBe(60000)
  })
})

describe("serializeCredential", () => {
  it("encode les tampons en base64url sans remplissage et ne garde que les champs présents", () => {
    const credential = {
      id: "cred-1", type: "public-key", rawId: bytes(255, 239, 1),
      response: { clientDataJSON: bytes(1, 2, 3), attestationObject: bytes(251, 255), getTransports: () => ["internal"] },
    } as unknown as Credential

    expect(serializeCredential(credential)).toEqual({
      id: "cred-1", rawId: "_-8B", type: "public-key",
      response: { clientDataJSON: "AQID", attestationObject: "-_8", transports: ["internal"] },
    })
  })

  it("une assertion de connexion porte les données d'authentificateur, la signature et l'utilisateur", () => {
    const credential = {
      id: "cred-2", type: "public-key", rawId: bytes(1),
      response: { clientDataJSON: bytes(1), authenticatorData: bytes(2), signature: bytes(3), userHandle: bytes(4) },
    } as unknown as Credential

    const out = serializeCredential(credential) as { response: Record<string, unknown> }

    expect(out.response).toEqual({ clientDataJSON: "AQ", authenticatorData: "Ag", signature: "Aw", userHandle: "BA" })
  })
})

describe("loginWithPasskey", () => {
  const assertion = { id: "cred-3", type: "public-key", rawId: bytes(9), response: { clientDataJSON: bytes(1), authenticatorData: bytes(2), signature: bytes(3) } }

  it("enchaîne options, signature par l'appareil et vérification, puis renvoie le jeton d'accès", async () => {
    let verifyBody: unknown
    server.use(
      http.post(apiUrl("/auth/passkey/login/options"), () => HttpResponse.json({ options: { challenge: "AQID" }, state: "s-1" })),
      http.post(apiUrl("/auth/passkey/login/verify"), async ({ request }) => { verifyBody = await request.json(); return HttpResponse.json({ access_token: "jwt-123" }) }),
    )
    stubCredentials({ get: async () => assertion })

    await expect(loginWithPasskey()).resolves.toBe("jwt-123")
    expect(verifyBody).toMatchObject({ state: "s-1", credential: { id: "cred-3", rawId: "CQ" } })
  })

  it("geste annulé sur l'appareil : erreur « connexion annulée », rien n'est vérifié", async () => {
    let verified = false
    server.use(
      http.post(apiUrl("/auth/passkey/login/options"), () => HttpResponse.json({ options: { challenge: "AQID" }, state: "s-1" })),
      http.post(apiUrl("/auth/passkey/login/verify"), () => { verified = true; return HttpResponse.json({ access_token: "x" }) }),
    )
    stubCredentials({ get: async () => null })

    await expect(loginWithPasskey()).rejects.toThrow()
    expect(verified).toBe(false)
  })

  it("serveur qui refuse : le détail du serveur devient le message de l'erreur", async () => {
    server.use(http.post(apiUrl("/auth/passkey/login/options"), () => HttpResponse.json({ detail: "Aucune passkey enregistrée" }, { status: 404 })))

    await expect(loginWithPasskey()).rejects.toThrow("Aucune passkey enregistrée")
  })

  it("réponse d'erreur sans détail lisible : message générique", async () => {
    server.use(http.post(apiUrl("/auth/passkey/login/options"), () => new HttpResponse("oups", { status: 500 })))

    await expect(loginWithPasskey()).rejects.toThrow()
  })
})
