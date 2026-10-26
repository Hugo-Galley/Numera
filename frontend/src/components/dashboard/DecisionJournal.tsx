import { useState } from "react"
import { BookMarked, Pencil, Plus, Trash2 } from "lucide-react"
import { format, parseISO } from "date-fns"
import { fr } from "date-fns/locale"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { FinancialEvent } from "@/components/dashboard/useDashboardData"
import { useSubmit } from "@/hooks/useSubmit"
import { api } from "@/lib/api"
import { todayLocal } from "@/lib/dates"
import { errorMessage } from "@/lib/utils"
import { useConfirm } from "@/providers/ConfirmProvider"

interface AccountOption {
  id: number
  name: string
  active?: boolean
}

interface Props {
  events: FinancialEvent[]
  accounts: AccountOption[]
  onChanged: () => void
}

const NO_ACCOUNT = "none"

/** Journal des décisions financières : notes datées affichées comme repères sur les courbes. */
export function DecisionJournal({ events, accounts, onChanged }: Props) {
  const confirm = useConfirm()
  const [editing, setEditing] = useState<FinancialEvent | null>(null)
  const [open, setOpen] = useState(false)
  const [day, setDay] = useState(todayLocal())
  const [title, setTitle] = useState("")
  const [note, setNote] = useState("")
  const [accountId, setAccountId] = useState(NO_ACCOUNT)

  const openForm = (event: FinancialEvent | null) => {
    setEditing(event)
    setDay(event?.date ?? todayLocal())
    setTitle(event?.title ?? "")
    setNote(event?.note ?? "")
    setAccountId(event?.account_id ? String(event.account_id) : NO_ACCOUNT)
    setOpen(true)
  }

  const [handleSave, saving] = useSubmit(async () => {
    if (!title.trim() || !day) {
      toast.error("Indiquez une date et un intitulé")
      return
    }
    const payload = {
      date: day,
      title: title.trim(),
      note: note.trim() || null,
      account_id: accountId === NO_ACCOUNT ? null : Number(accountId),
    }
    try {
      if (editing) await api.patch(`/financial-events/${editing.id}`, payload)
      else await api.post("/financial-events", payload)
      toast.success(editing ? "Décision modifiée" : "Décision ajoutée au journal")
      setOpen(false)
      onChanged()
    } catch (e) {
      toast.error(errorMessage(e, "Impossible d'enregistrer la décision"))
    }
  })

  const handleDelete = async (event: FinancialEvent) => {
    if (!(await confirm(`Supprimer « ${event.title} » du journal ?`))) return
    try {
      await api.delete(`/financial-events/${event.id}`)
      toast.success("Décision supprimée")
      onChanged()
    } catch (e) {
      toast.error(errorMessage(e, "Impossible de supprimer la décision"))
    }
  }

  const selectableAccounts = accounts.filter((a) => a.active !== false || String(a.id) === accountId)

  return (
    <Card className="shadow-sm border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b p-4 pb-3 md:p-6 md:pb-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <BookMarked className="h-5 w-5 text-slate-400" />
            <CardTitle className="text-lg">Journal des décisions</CardTitle>
          </div>
          <Button size="sm" variant="outline" className="h-10 md:h-8" onClick={() => openForm(null)}>
            <Plus className="mr-1.5 h-4 w-4" /> Ajouter
          </Button>
        </div>
        <CardDescription>Résiliation, hausse d'épargne, changement d'allocation… repérés sur les courbes (⚑).</CardDescription>
      </CardHeader>
      <CardContent className="p-3 md:p-6">
        {events.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center text-sm text-slate-400">
            <BookMarked className="h-8 w-8 text-slate-300" />
            <p>Notez vos décisions pour retrouver plus tard pourquoi une courbe a changé.</p>
          </div>
        ) : (
          <ul className="max-h-[360px] space-y-2 overflow-y-auto">
            {events.map((event) => (
              <li key={event.id} className="group flex gap-3 rounded-xl border p-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold tabular-nums text-slate-500">
                    {format(parseISO(event.date), "d MMM yyyy", { locale: fr })}
                    {event.account_name && <span className="font-normal text-slate-400"> · {event.account_name}</span>}
                  </p>
                  <p className="font-medium text-slate-900">{event.title}</p>
                  {event.note && <p className="whitespace-pre-line text-sm text-slate-500">{event.note}</p>}
                </div>
                <div className="flex shrink-0 gap-1 md:opacity-0 md:transition-opacity md:group-hover:opacity-100">
                  <Button size="icon" variant="ghost" className="h-10 w-10 md:h-8 md:w-8" aria-label="Modifier" onClick={() => openForm(event)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button size="icon" variant="ghost" className="h-10 w-10 md:h-8 md:w-8 text-rose-600" aria-label="Supprimer" onClick={() => handleDelete(event)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[440px] rounded-2xl">
          <DialogHeader>
            <DialogTitle>{editing ? "Modifier la décision" : "Nouvelle décision"}</DialogTitle>
            <DialogDescription>Une note datée, sans effet sur les calculs.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="event-date">Date</Label>
              <Input id="event-date" type="date" value={day} onChange={(e) => setDay(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="event-title">Intitulé</Label>
              <Input id="event-title" maxLength={200} placeholder="Ex : résiliation de la salle de sport" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="event-note">Note (facultatif)</Label>
              <textarea
                id="event-note"
                maxLength={1000}
                rows={3}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="w-full rounded-md border border-slate-200 bg-white p-3 text-base md:text-sm"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="event-account">Compte concerné (facultatif)</Label>
              <Select value={accountId} onValueChange={setAccountId}>
                <SelectTrigger id="event-account"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_ACCOUNT}>Aucun</SelectItem>
                  {selectableAccounts.map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>{a.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Annuler</Button>
            <Button onClick={() => handleSave()} disabled={saving} className="bg-slate-900 text-white">
              {saving ? "Enregistrement…" : "Enregistrer"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
