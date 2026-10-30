/** Rendu d'un composant avec les providers de l'app (même ordre que `App.tsx`). */
import type { ReactElement, ReactNode } from "react"
import { render, type RenderOptions } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { safeStorage } from "@/lib/storage"
import { AuthProvider } from "@/providers/AuthProvider"
import { ConfirmProvider } from "@/providers/ConfirmProvider"
import { UIProvider } from "@/providers/UIProvider"
import { makeToken } from "./token"

interface ProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  /** Adresse initiale du MemoryRouter (« /accounts/1?tab=x »). */
  route?: string
  /** `true` : session valide d'une heure ; `{ expInMinutes }` pour une autre échéance ; `{ token }` pour un jeton précis. */
  auth?: boolean | { expInMinutes?: number; token?: string }
}

export function renderWithProviders(ui: ReactElement, { route = "/", auth = false, ...options }: ProvidersOptions = {}) {
  if (auth) {
    const settings = auth === true ? {} : auth
    safeStorage.setItem("token", settings.token ?? makeToken({ expInMinutes: settings.expInMinutes }))
  }

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <UIProvider>
      <AuthProvider>
        <ConfirmProvider>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
          <Toaster />
        </ConfirmProvider>
      </AuthProvider>
    </UIProvider>
  )

  return { user: userEvent.setup(), ...render(ui, { wrapper: Wrapper, ...options }) }
}
