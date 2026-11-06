import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"
import { FormMainFields } from "./FormMainFields"
import { FormSecurityFields } from "./FormSecurityFields"
import { FormAmountFields } from "./FormAmountFields"
import { FormScheduleFields } from "./FormScheduleFields"

/** Dialogue de création / modification d'une récurrence. */
export function RecurringFormDialog({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { t } = useTranslation("recurring")
  const { editingTx, handleSubmit, handleSubmitBusy, isFormOpen, setIsFormOpen } = ctx
  return (
    <>
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-md max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] overflow-y-auto max-sm:[&_input]:text-base max-sm:[&_textarea]:text-base">
          <DialogHeader>
            <DialogTitle>{editingTx ? i18n.t("misc.editRecurrence", { ns: "recurring" }) : i18n.t("misc.newRecurrence", { ns: "recurring" })}</DialogTitle>
            <DialogDescription>
              {t("recurringFormDialog.configurezUneTransactionQuiSe")}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <FormMainFields ctx={ctx} />

            <FormSecurityFields ctx={ctx} />

            <FormAmountFields ctx={ctx} />

            <FormScheduleFields ctx={ctx} />
          </div>

          <DialogFooter>
            <Button variant="outline" className="h-11 sm:h-10" onClick={() => setIsFormOpen(false)}>{t("recurringFormDialog.annuler")}</Button>
            <Button className="h-11 sm:h-10" onClick={() => handleSubmit()} disabled={handleSubmitBusy}>{handleSubmitBusy ? t("recurringFormDialog.enregistrement") : t("recurringFormDialog.enregistrer")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
