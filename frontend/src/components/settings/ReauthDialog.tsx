import i18n from "i18next"
import { useCallback, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export interface Reauth {
  current_password: string
  code?: string
}

interface Request {
  title: string
  description: string
  resolve: (value: Reauth | null) => void
}

/**
 * Ré-authentification avant une action sensible (passkeys, destination des notifications) : un jeton de
 * session volé ne doit pas suffire. `ask()` résout les identifiants saisis, ou null si l'utilisateur annule.
 * Le code n'est exigé par le serveur que si la double authentification est active.
 */
export function useReauth() {
  const [request, setRequest] = useState<Request | null>(null)
  const [password, setPassword] = useState("")
  const [code, setCode] = useState("")
  const pending = useRef<Request | null>(null)

  const ask = useCallback(
    (title: string, description: string) =>
      new Promise<Reauth | null>((resolve) => {
        const next = { title, description, resolve }
        pending.current = next
        setPassword("")
        setCode("")
        setRequest(next)
      }),
    [],
  )

  const close = (value: Reauth | null) => {
    pending.current?.resolve(value)
    pending.current = null
    setRequest(null)
    setPassword("")
    setCode("")
  }

  const dialog = (
    <Dialog open={request !== null} onOpenChange={(open) => !open && close(null)}>
      <DialogContent>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (password) close({ current_password: password, ...(code.trim() ? { code: code.trim() } : {}) })
          }}
          className="space-y-4"
        >
          <DialogHeader>
            <DialogTitle>{request?.title}</DialogTitle>
            <DialogDescription>{request?.description}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="reauth-password">{i18n.t("reauthDialog.motDePasseActuel", { ns: "settings" })}</Label>
            <Input id="reauth-password" type="password" autoComplete="current-password" autoFocus value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="reauth-code">{i18n.t("reauthDialog.codeDeDoubleAuthentificationSi", { ns: "settings" })}</Label>
            <Input id="reauth-code" inputMode="text" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="ghost" onClick={() => close(null)}>{i18n.t("reauthDialog.annuler", { ns: "settings" })}</Button>
            <Button type="submit" disabled={!password}>{i18n.t("reauthDialog.confirmer", { ns: "settings" })}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )

  return { ask, dialog }
}
