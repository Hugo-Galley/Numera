import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { AccountDetailView } from "./useAccountDetail"

/** Dialogue de modification groupée (catégorie, récurrence, tags). */
export function BulkEditDialog({ ctx }: { ctx: AccountDetailView }) {
  const { t } = useTranslation("accountDetail")
  const { t: tc } = useTranslation("common")
  const { availableTags, bulkCategory, bulkRecurring, bulkTagAction, bulkTagIds, categories, handleBulkUpdate, isBulkEditDialogOpen, selectedIds, setBulkCategory, setBulkRecurring, setBulkTagAction, setBulkTagIds, setIsBulkEditDialogOpen } = ctx
  return (
    <>
      {/* Bulk Edit Dialog */}
      <Dialog open={isBulkEditDialogOpen} onOpenChange={setIsBulkEditDialogOpen}>
        <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("tx.bulk.editTitle")}</DialogTitle>
            <DialogDescription>
              {t("tx.bulk.editHint", { count: selectedIds.length })}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-6 py-4">
            <div className="space-y-2">
              <Label>{t("tx.bulk.category")}</Label>
              <Select value={bulkCategory} onValueChange={setBulkCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="keep">{t("tx.bulk.keep")}</SelectItem>
                  <SelectItem value="none">{t("tx.bulk.noCategory")}</SelectItem>
                  {categories.filter((cat) => !cat.archived).map((cat) => (
                    <SelectItem key={cat.id} value={String(cat.id)}>
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: cat.color || "#cbd5e1" }} />
                        {cat.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t("tx.bulk.recurring")}</Label>
              <Select value={bulkRecurring} onValueChange={setBulkRecurring}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="keep">{t("tx.bulk.keep")}</SelectItem>
                  <SelectItem value="true">{t("tx.bulk.recurringYes")}</SelectItem>
                  <SelectItem value="false">{t("tx.bulk.recurringNo")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4 pt-2 border-t">
              <div className="flex items-center justify-between">
                <Label>{t("tx.tags")}</Label>
                <Select value={bulkTagAction} onValueChange={(v) => setBulkTagAction(v as typeof bulkTagAction)}>
                  <SelectTrigger className="w-[150px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="keep">{t("tx.bulk.keep")}</SelectItem>
                    <SelectItem value="replace">{t("tx.bulk.replaceWith")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {bulkTagAction === "replace" && (
                <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                  {availableTags.filter((tag) => !tag.archived).map((tag) => (
                    <div key={tag.id} className="flex items-center space-x-2">
                      <Checkbox 
                        id={`bulk-tag-${tag.id}`} 
                        checked={bulkTagIds.includes(tag.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setBulkTagIds([...bulkTagIds, tag.id])
                          } else {
                            setBulkTagIds(bulkTagIds.filter(tid => tid !== tag.id))
                          }
                        }}
                      />
                      <label
                        htmlFor={`bulk-tag-${tag.id}`}
                        className="text-xs font-medium leading-none cursor-pointer"
                      >
                        <Badge 
                          variant="outline" 
                          className="px-2 py-0 h-5 border-none text-white font-bold text-[9px]"
                          style={{ backgroundColor: tag.color || "#64748b" }}
                        >
                          {tag.name}
                        </Badge>
                      </label>
                    </div>
                  ))}
                  {availableTags.length === 0 && (
                    <p className="text-[10px] text-slate-400">{t("tx.bulk.noTags")}</p>
                  )}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBulkEditDialogOpen(false)}>{tc("actions.cancel")}</Button>
            <Button onClick={handleBulkUpdate} className="bg-slate-900 text-white">{t("tx.bulk.apply")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
