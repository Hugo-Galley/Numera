import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Pencil, Search, ShoppingBag, Trash2 } from "lucide-react"
import type { MerchantsTabCtx } from "./useMerchantsTab"

/** Recherche et liste des marchands. */
export function MerchantsList({ ctx }: { ctx: MerchantsTabCtx }) {
  const { filteredMerchants, handleDeleteMerchant, handleEditClick, loading, search, setSearch } = ctx
  return (
    <>
      <div className="lg:col-span-3 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input 
            placeholder="Rechercher un marchand ou un libellé..." 
            className="pl-10 bg-white border-slate-200 h-12 rounded-xl"
            type="search"
            enterKeyHint="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {loading ? (
          <div className="text-center py-20 text-slate-400">Chargement...</div>
        ) : (
          <div className="grid gap-4">
            {filteredMerchants.map(m => (
              <Card key={m.id} className="group hover:border-slate-300 transition-all border-slate-100 shadow-sm overflow-hidden">
                <CardContent className="p-0">
                  <div className="p-3 pl-4 md:p-4 flex items-center justify-between gap-2 md:gap-4">
                    <div className="flex min-w-0 items-center gap-3 md:gap-4">
                      <div className="h-10 w-10 shrink-0 rounded-xl flex items-center justify-center text-white" style={{ backgroundColor: m.color || "#64748b" }}>
                        <ShoppingBag className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-slate-900 truncate">{m.name}</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {m.aliases.length > 0 ? (
                            m.aliases.map(a => (
                              <Badge key={a.id} variant="secondary" className="max-w-full truncate bg-slate-50 text-slate-500 border-slate-200 text-[10px] font-medium h-5">
                                {a.label}
                              </Badge>
                            ))
                          ) : (
                            <p className="text-[10px] text-slate-400 italic">Aucune variante définie</p>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-1 md:gap-2 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                      <Button aria-label="Modifier" variant="ghost" size="sm" onClick={() => handleEditClick(m)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-500 hover:text-slate-900">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button aria-label="Supprimer" variant="ghost" size="sm" onClick={() => handleDeleteMerchant(m.id)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {filteredMerchants.length === 0 && (
              <div className="py-20 text-center bg-slate-50 rounded-3xl border-2 border-dashed border-slate-200">
                <ShoppingBag className="h-10 w-10 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 font-medium">Aucun marchand trouvé.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
