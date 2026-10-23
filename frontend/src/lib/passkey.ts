// WebAuthn (Face ID / Touch ID) : conversions base64url <-> ArrayBuffer autour de navigator.credentials.
import { API_BASE } from "@/lib/api"

export const passkeySupported = () => typeof window !== "undefined" && !!window.PublicKeyCredential && !!navigator.credentials

function toBuffer(value: string): ArrayBuffer {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/")
  const binary = atob(base64 + "=".repeat((4 - (base64.length % 4)) % 4))
  return Uint8Array.from(binary, (c) => c.charCodeAt(0)).buffer
}

function toBase64Url(buffer: ArrayBuffer): string {
  let binary = ""
  new Uint8Array(buffer).forEach((b) => (binary += String.fromCharCode(b)))
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")
}

const descriptors = (list?: any[]) => list?.map((d) => ({ ...d, id: toBuffer(d.id) }))

export function createCredential(options: any): Promise<Credential | null> {
  return navigator.credentials.create({
    publicKey: {
      ...options,
      challenge: toBuffer(options.challenge),
      user: { ...options.user, id: toBuffer(options.user.id) },
      excludeCredentials: descriptors(options.excludeCredentials),
    },
  })
}

export function getCredential(options: any): Promise<Credential | null> {
  return navigator.credentials.get({
    publicKey: {
      ...options,
      challenge: toBuffer(options.challenge),
      allowCredentials: descriptors(options.allowCredentials),
    },
  })
}

/** Sérialise le résultat de create()/get() au format JSON attendu par le backend. */
export function serializeCredential(credential: Credential): Record<string, unknown> {
  const pk = credential as PublicKeyCredential
  const response = pk.response as AuthenticatorAttestationResponse & AuthenticatorAssertionResponse
  const out: Record<string, unknown> = {
    id: pk.id,
    rawId: toBase64Url(pk.rawId),
    type: pk.type,
    response: { clientDataJSON: toBase64Url(response.clientDataJSON) },
  }
  const r = out.response as Record<string, unknown>
  if (response.attestationObject) r.attestationObject = toBase64Url(response.attestationObject)
  if (response.authenticatorData) r.authenticatorData = toBase64Url(response.authenticatorData)
  if (response.signature) r.signature = toBase64Url(response.signature)
  if (response.userHandle) r.userHandle = toBase64Url(response.userHandle)
  if (typeof response.getTransports === "function") r.transports = response.getTransports()
  return out
}

/** Connexion complète par passkey ; renvoie le jeton d'accès. */
export async function loginWithPasskey(): Promise<string> {
  const post = async (path: string, body?: unknown) => {
    const response = await fetch(`${API_BASE}/auth/passkey/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Connexion par passkey impossible")
    return data
  }
  const { options, state } = await post("login/options")
  const credential = await getCredential(options)
  if (!credential) throw new Error("Connexion annulée")
  const { access_token } = await post("login/verify", { state, credential: serializeCredential(credential) })
  return access_token
}
