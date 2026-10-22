import React, { createContext, useCallback, useContext, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface ConfirmOptions {
  title?: string
  description?: string
  confirmLabel?: string
  destructive?: boolean
}

type ConfirmFn = (message: string, options?: ConfirmOptions) => Promise<boolean>

const ConfirmContext = createContext<ConfirmFn | undefined>(undefined)

/** Remplace `window.confirm()` par une boîte de dialogue de l'app : `if (!(await confirm("…"))) return`. */
export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [request, setRequest] = useState<(ConfirmOptions & { message: string }) | null>(null)
  const resolver = useRef<((value: boolean) => void) | null>(null)

  const confirm = useCallback<ConfirmFn>((message, options) => {
    resolver.current?.(false)
    setRequest({ message, ...options })
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve
    })
  }, [])

  const close = (value: boolean) => {
    resolver.current?.(value)
    resolver.current = null
    setRequest(null)
  }

  // Par défaut, une confirmation sert à supprimer : bouton rouge « Supprimer »
  const destructive = request?.destructive ?? true

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Dialog open={request !== null} onOpenChange={(open) => !open && close(false)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{request?.title ?? "Confirmer"}</DialogTitle>
            <DialogDescription>{request?.message}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => close(false)}>Annuler</Button>
            <Button
              variant={destructive ? "destructive" : "default"}
              onClick={() => close(true)}
              autoFocus
            >
              {request?.confirmLabel ?? (destructive ? "Supprimer" : "Confirmer")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ConfirmContext.Provider>
  )
}

export function useConfirm(): ConfirmFn {
  const context = useContext(ConfirmContext)
  if (!context) throw new Error("useConfirm must be used within a ConfirmProvider")
  return context
}
