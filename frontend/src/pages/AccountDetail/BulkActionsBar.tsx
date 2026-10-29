import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Pencil, Trash2, X } from "lucide-react"
import { Separator } from "@/components/ui/separator"
import { api } from "@/lib/api"
import { toast } from "sonner"
import type { AccountDetailView } from "./useAccountDetail"

/** Barre flottante des actions groupées sur la sélection. */
export function BulkActionsBar({ ctx }: { ctx: AccountDetailView }) {
  const { confirm, loadData, selectedIds, setIsBulkEditDialogOpen, setSelectedIds, transactions } = ctx
  return (
    <>
      {/* Bulk Actions Floating Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-[calc(4.75rem+env(safe-area-inset-bottom))] left-1/2 z-50 flex w-[calc(100%-2rem)] -translate-x-1/2 items-center justify-between gap-2 rounded-2xl border border-slate-800 bg-slate-900 px-3 py-2 text-white shadow-2xl md:bottom-8 md:w-auto md:justify-start md:gap-6 md:px-6 md:py-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center gap-2 pr-2 border-r border-slate-700 md:pr-4">
            <Badge className="bg-emerald-500 text-white border-none">{selectedIds.length}</Badge>
            <span className="hidden text-sm font-medium sm:inline">sélectionnés</span>
          </div>

          <div className="flex items-center gap-2">
            <Button 
              size="sm" 
              variant="ghost" 
              className="h-10 text-white hover:bg-slate-800 gap-2 md:h-9"
              onClick={() => setIsBulkEditDialogOpen(true)}
            >
              <Pencil className="h-4 w-4" />
              Modifier
            </Button>

            <Button 
              size="sm" 
              variant="ghost" 
              className="h-10 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 gap-2 md:h-9"
              onClick={async () => {
                if (await confirm(`Supprimer ${selectedIds.length} transactions ?`)) {
                  try {
                    await api.post("/transactions/bulk-delete", { ids: selectedIds })
                    toast.success(`${selectedIds.length} transactions supprimées`)
                    setSelectedIds([])
                    await loadData({ quiet: true })
                  } catch (e) {
                    toast.error("Erreur lors de la suppression groupée")
                  }
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
              Supprimer
            </Button>
          </div>

          <Separator orientation="vertical" className="hidden h-6 bg-slate-700 md:block" />

          <Button aria-label="Fermer" 
            size="sm" 
            variant="ghost" 
            className="h-10 w-10 text-slate-400 hover:text-white p-2 md:h-9 md:w-auto"
            onClick={() => setSelectedIds([])}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}
    </>
  )
}
