import { useState } from "react"
import { Check, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectSeparator, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Category } from "./types"

const NONE = "__none__"
const NEW = "__new__"

/** Groupes Sankey déjà utilisés par les catégories, sans doublon, triés. */
export function sankeyGroups(categories: Pick<Category, "group">[]): string[] {
  const names = new Set<string>()
  for (const cat of categories) {
    const name = cat.group?.trim()
    if (name) names.add(name)
  }
  return [...names].sort((a, b) => a.localeCompare(b, "fr", { sensitivity: "base" }))
}

interface Props {
  id: string
  value: string
  onChange: (value: string) => void
  groups: string[]
}

/** Liste fermée des groupes Sankey existants, avec « Nouveau groupe » en bas pour en créer un. */
export function SankeyGroupSelect({ id, value, onChange, groups }: Props) {
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState("")
  // Un groupe tout juste créé (pas encore enregistré) doit rester sélectionnable
  const options = value && !groups.includes(value) ? [...groups, value] : groups

  const confirm = () => {
    const name = draft.trim()
    if (name) {
      // Réutilise l'orthographe existante plutôt que de créer « loisirs » à côté de « Loisirs »
      const existing = groups.find((g) => g.localeCompare(name, "fr", { sensitivity: "base" }) === 0)
      onChange(existing ?? name)
    }
    setCreating(false)
    setDraft("")
  }

  if (creating) {
    return (
      <div className="flex gap-2">
        <Input
          id={id}
          autoFocus
          aria-label="Nom du nouveau groupe"
          placeholder="Ex: Vie courante, Loisirs..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); confirm() }
            if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setCreating(false); setDraft("") }
          }}
          className="bg-slate-50 border-slate-200"
        />
        <Button type="button" size="icon" variant="outline" aria-label="Valider le groupe" onClick={confirm}>
          <Check className="h-4 w-4" />
        </Button>
        <Button type="button" size="icon" variant="ghost" aria-label="Annuler" onClick={() => { setCreating(false); setDraft("") }}>
          <X className="h-4 w-4" />
        </Button>
      </div>
    )
  }

  return (
    <Select
      value={value || NONE}
      onValueChange={(v) => {
        if (v === NEW) setCreating(true)
        else onChange(v === NONE ? "" : v)
      }}
    >
      <SelectTrigger id={id} className="bg-slate-50 border-slate-200">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE}>Aucun groupe</SelectItem>
        {options.map((g) => (
          <SelectItem key={g} value={g}>{g}</SelectItem>
        ))}
        <SelectSeparator />
        <SelectItem value={NEW}>
          <span className="flex items-center gap-2 text-slate-500"><Plus className="h-4 w-4" /> Nouveau groupe</span>
        </SelectItem>
      </SelectContent>
    </Select>
  )
}
