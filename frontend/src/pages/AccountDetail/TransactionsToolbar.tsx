import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { History, Search, Tag } from "lucide-react"
import { Input } from "@/components/ui/input"
import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { AccountDetailView } from "./useAccountDetail"

/** En-tête de la liste des transactions (titre, tri, sélection). */
export function TransactionsToolbar({ ctx }: { ctx: AccountDetailView }) {
  const { t } = useTranslation("accountDetail")
  const { t: tc } = useTranslation("common")
  const { availableTags, categories, filterCategory, filterTags, filterType, search, setFilterCategory, setFilterTags, setFilterType, setSearch } = ctx
  return (
    <>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2"><History className="h-5 w-5 text-slate-400" /> {t("tx.history")}</h2>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center sm:gap-3">
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="h-11 w-full bg-white sm:h-9 sm:w-[120px]">
              <SelectValue placeholder={t("tx.type")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("tx.allTypes")}</SelectItem>
              <SelectItem value="Sortie">{tc("txTypes.Sortie")}</SelectItem>
              <SelectItem value="Entree">{tc("txTypes.Entree")}</SelectItem>
              <SelectItem value="Virement">{tc("txTypes.Virement")}</SelectItem>
              <SelectItem value="Solde Initial">{tc("txTypes.initial")}</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterCategory} onValueChange={setFilterCategory}>
            <SelectTrigger className="h-11 w-full bg-white sm:h-9 sm:w-[150px]">
              <SelectValue placeholder={t("tx.category")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("tx.allCategories")}</SelectItem>
              {categories.map(c => (
                <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {availableTags.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-11 w-full bg-white gap-2 sm:h-9 sm:w-auto">
                  <Tag className="h-4 w-4" />
                  {filterTags.length === 0 ? t("tx.tags") : t("tx.tagsCount", { count: filterTags.length })}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56">
                <DropdownMenuLabel>{t("tx.filterByTags")}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {availableTags.map((tag) => (
                  <DropdownMenuCheckboxItem
                    key={tag.id}
                    checked={filterTags.includes(tag.id)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setFilterTags([...filterTags, tag.id])
                      } else {
                        setFilterTags(filterTags.filter(id => id !== tag.id))
                      }
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full" style={{ backgroundColor: tag.color || "#64748b" }} />
                      {tag.name}
                    </div>
                  </DropdownMenuCheckboxItem>
                ))}
                {filterTags.length > 0 && (
                  <>
                    <DropdownMenuSeparator />
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="w-full text-xs h-8" 
                      onClick={() => setFilterTags([])}
                    >
                      {t("tx.clearFilters")}
                    </Button>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          <div className="relative col-span-2 w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder={t("tx.search")} className="pl-10 bg-white h-11 text-base sm:h-9 sm:text-sm" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
      </div>
    </>
  )
}
