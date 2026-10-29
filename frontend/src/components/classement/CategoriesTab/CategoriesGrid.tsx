import { Archive, ArchiveRestore, Pencil, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { IconComponent } from "@/components/dashboard/IconComponent"
import { categoryTypeLabel } from "@/lib/labels"
import type { CategoriesTabCtx } from "./useCategoriesTab"

/** Cartes des catégories. */
export function CategoriesGrid({ ctx }: { ctx: CategoriesTabCtx }) {
  const { categories, handleDeleteCategory, handleEditClick, handleToggleArchiveCategory, showArchivedCats } = ctx
  return (
    <>
      <div className="grid gap-3 md:gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {categories.filter((cat) => showArchivedCats || !cat.archived).map((cat) => (
          <Card key={cat.id} className={`group hover:border-slate-300 transition-all shadow-sm border-slate-100 overflow-hidden ${cat.archived ? "opacity-60" : ""}`}>
            <CardContent className="p-0">
              <div className="p-3 pl-4 md:p-4 flex items-center gap-3 md:gap-4">
                <div className="h-12 w-12 shrink-0 rounded-2xl flex items-center justify-center shadow-sm" style={{ backgroundColor: cat.color || "#64748b" }}>
                  <IconComponent name={cat.icon} className="h-6 w-6 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-slate-900 truncate">{cat.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className={`
                      text-[9px] uppercase font-black border-none px-0
                      ${cat.type === 'depense' ? 'text-rose-500' : ''}
                      ${cat.type === 'revenu' ? 'text-emerald-500' : ''}
                      ${cat.type === 'neutre' ? 'text-slate-400' : ''}
                    `}>
                      {categoryTypeLabel(cat.type)}
                    </Badge>
                    {cat.group && (
                      <Badge variant="secondary" className="text-[9px] h-4 px-1 bg-slate-100 text-slate-500 border-none font-bold">
                        {cat.group}
                      </Badge>
                    )}
                  </div>
                  {cat.monthly_limit != null && (
                    <p className="text-[10px] text-amber-600 font-semibold mt-0.5">{cat.monthly_limit}€/mois</p>
                  )}
                  {cat.archived && <p className="text-[10px] text-slate-400 font-semibold mt-0.5">Archivée</p>}
                </div>
                <div className="flex shrink-0 gap-0 md:hidden">
                  <Button variant="ghost" size="sm" onClick={() => handleEditClick(cat)} aria-label="Modifier" className="h-10 w-10 p-0 text-slate-500">
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleToggleArchiveCategory(cat)} aria-label={cat.archived ? "Réactiver" : "Archiver"} title={cat.archived ? "Réactiver" : "Archiver"} className="h-10 w-10 p-0 text-slate-500">
                    {cat.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDeleteCategory(cat.id)} aria-label="Supprimer" className="h-10 w-10 p-0 text-rose-500 hover:bg-rose-50">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="hidden md:flex px-4 py-3 bg-slate-50/50 border-t justify-between items-center md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                <p className="text-[10px] text-slate-400 font-medium">ID: #{cat.id}</p>
                <div className="flex gap-1">
                  <Button aria-label="Modifier" variant="ghost" size="sm" onClick={() => handleEditClick(cat)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-500 hover:text-slate-900">
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button aria-label={cat.archived ? "Réactiver" : "Archiver"} title={cat.archived ? "Réactiver" : "Archiver"} variant="ghost" size="sm" onClick={() => handleToggleArchiveCategory(cat)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-slate-500 hover:text-slate-900">
                    {cat.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
                  </Button>
                  <Button aria-label="Supprimer" variant="ghost" size="sm" onClick={() => handleDeleteCategory(cat.id)} className="h-10 w-10 md:h-8 md:w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  )
}
