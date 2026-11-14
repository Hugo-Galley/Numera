/** Bandeau de vérification des comptes : comptes périmés, validation sans changement, snapshot, saisie du solde. */
import { screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { AccountVerificationBanner } from "@/components/dashboard/AccountVerificationBanner"
import { LocationDisplay } from "@/test/support/LocationDisplay"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const NOW = new Date("2026-06-15T10:00:00")
const daysAgo = (n: number) => new Date(NOW.getTime() - n * 86_400_000).toISOString()

type Props = React.ComponentProps<typeof AccountVerificationBanner>
const account = (over: Partial<Props["accounts"][number]> & { id: number; name: string }): Props["accounts"][number] =>
  ({ type: "courant", last_verified_at: daysAgo(20), active: true, ...over })

function setup(accounts: Props["accounts"]) {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(NOW)
  const onAccountVerified = vi.fn()
  const view = renderWithProviders(
    <>
      <AccountVerificationBanner accounts={accounts} onAccountVerified={onAccountVerified} />
      <LocationDisplay />
      <Routes><Route path="*" element={null} /></Routes>
    </>,
    { auth: true },
  )
  return { onAccountVerified, ...view }
}

afterEach(() => vi.useRealTimers())

describe("AccountVerificationBanner", () => {
  it("rien à signaler : aucun bandeau (comptes récents ou inactifs)", () => {
    setup([account({ id: 1, name: "Récent", last_verified_at: daysAgo(14) }), account({ id: 2, name: "Clos", active: false })])

    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })

  it("replié : compte et noms des comptes périmés (≥ 15 jours ou jamais vérifiés)", () => {
    setup([
      account({ id: 1, name: "Courant" }),
      account({ id: 2, name: "Livret", last_verified_at: "" }),
      account({ id: 3, name: "Frais", last_verified_at: daysAgo(15) }),
      account({ id: 4, name: "Récent", last_verified_at: daysAgo(3) }),
    ])

    const toggle = screen.getByRole("button", { expanded: false })
    expect(toggle).toHaveTextContent("3 comptes à mettre à jour")
    expect(toggle).toHaveTextContent("Courant, Livret, Frais")
    expect(screen.queryByText("Rien n'a bougé")).not.toBeInTheDocument()
  })

  it("déplié : ancienneté (singulier, pluriel, jamais) et lien vers le compte", async () => {
    const { user } = setup([
      account({ id: 1, name: "Courant", last_verified_at: daysAgo(20) }),
      account({ id: 2, name: "Livret", last_verified_at: "pas une date" }),
    ])

    await user.click(screen.getByRole("button", { expanded: false }))
    expect(screen.getByText("Dernière maj: il y a 20 jours")).toBeInTheDocument()
    expect(screen.getByText("Jamais vérifié")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Courant" }))
    expect(screen.getByLabelText("adresse")).toHaveTextContent("/accounts/1")
  })

  it("« Rien n'a bougé » : POST de vérification puis parent prévenu", async () => {
    const verified: string[] = []
    server.use(http.post(apiUrl("/accounts/1/verify"), ({ request }) => { verified.push(new URL(request.url).pathname); return HttpResponse.json({}) }))
    const { user, onAccountVerified } = setup([account({ id: 1, name: "Courant" })])

    await user.click(screen.getByRole("button", { expanded: false }))
    await user.click(screen.getByRole("button", { name: "Rien n'a bougé" }))

    await waitFor(() => expect(onAccountVerified).toHaveBeenCalledTimes(1))
    expect(verified).toHaveLength(1)
  })

  it("échec de la validation : toast d'erreur, parent non prévenu, bouton de nouveau actif", async () => {
    server.use(http.post(apiUrl("/accounts/1/verify"), () => HttpResponse.json({ detail: "Compte verrouillé" }, { status: 409 })))
    vi.spyOn(console, "error").mockImplementation(() => {})
    const { user, onAccountVerified } = setup([account({ id: 1, name: "Courant" })])

    await user.click(screen.getByRole("button", { expanded: false }))
    await user.click(screen.getByRole("button", { name: "Rien n'a bougé" }))

    expect(await screen.findByText("Compte verrouillé")).toBeInTheDocument()
    expect(onAccountVerified).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: "Rien n'a bougé" })).toBeEnabled()
  })

  it("compte d'investissement ou assurance-vie : « Faire un snapshot » ouvre le compte, sans validation directe", async () => {
    const { user } = setup([account({ id: 7, name: "PEA", type: "investissement" }), account({ id: 8, name: "AV", type: "assurance_vie" })])

    await user.click(screen.getByRole("button", { expanded: false }))
    expect(screen.queryByRole("button", { name: "Rien n'a bougé" })).not.toBeInTheDocument()
    await user.click(screen.getAllByRole("button", { name: /Faire un snapshot/ })[1])

    expect(screen.getByLabelText("adresse")).toHaveTextContent("/accounts/8")
  })

  it("« Saisir le solde » ouvre le rapprochement du compte, qui se ferme sans enregistrer", async () => {
    const { user } = setup([account({ id: 1, name: "Courant", currency: "USD" })])

    await user.click(screen.getByRole("button", { expanded: false }))
    await user.click(screen.getByRole("button", { name: "Saisir le solde" }))
    expect(await screen.findByLabelText("Solde banque (USD)")).toBeInTheDocument()

    await user.keyboard("{Escape}")
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  })
})
