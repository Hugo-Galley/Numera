import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"
import { FormMainFields } from "./FormMainFields"
import { FormSecurityFields } from "./FormSecurityFields"
import { FormAmountFields } from "./FormAmountFields"
import { FormScheduleFields } from "./FormScheduleFields"

/** Dialogue de création / modification d'une récurrence. */
export function RecurringFormDialog({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { editingTx, handleSubmit, handleSubmitBusy, isFormOpen, setIsFormOpen } = ctx
  return (
    <>
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-md max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] overflow-y-auto max-sm:[&_input]:text-base max-sm:[&_textarea]:text-base">
          <DialogHeader>
            <DialogTitle>{editingTx ? "Modifier" : "Nouvelle"} récurrence</DialogTitle>
            <DialogDescription>
              Configurez une transaction qui se répète automatiquement.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <FormMainFields ctx={ctx} />

            <FormSecurityFields ctx={ctx} />

            <FormAmountFields ctx={ctx} />

            <FormScheduleFields ctx={ctx} />
          </div>

          <DialogFooter>
            <Button variant="outline" className="h-11 sm:h-10" onClick={() => setIsFormOpen(false)}>Annuler</Button>
            <Button className="h-11 sm:h-10" onClick={() => handleSubmit()} disabled={handleSubmitBusy}>{handleSubmitBusy ? "Enregistrement…" : "Enregistrer"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
