import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useTranslation } from "react-i18next"
import { ImportFlow } from "./ImportFlow"

type ImportDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Compte présélectionné ; sans compte, le formulaire demande lequel */
  accountId?: number
  onImported?: () => void
}

// Import d'un relevé CSV, ouvert depuis la page d'un compte (ou ⌘K → /accounts?import=1)
export function ImportDialog({ open, onOpenChange, accountId, onImported }: ImportDialogProps) {
  const { t } = useTranslation("import")
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] overflow-y-auto sm:max-w-6xl [&_input]:text-base md:[&_input]:text-sm">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">{t("title")}</DialogTitle>
          <DialogDescription>
            {t("subtitle")}
          </DialogDescription>
        </DialogHeader>
        {open && <ImportFlow accountId={accountId} onImported={onImported} />}
      </DialogContent>
    </Dialog>
  )
}
