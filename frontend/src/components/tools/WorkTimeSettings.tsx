import { useEffect, useState } from "react"
import { Clock, Save } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import { useWorkTime, type WorkTime } from "@/providers/WorkTimeProvider"

/** Réglages du « prix en heures de travail » (jours travaillés par an, heures par jour). */
export function WorkTimeSettings() {
  const { workTime, refresh } = useWorkTime()
  const [days, setDays] = useState("")
  const [hours, setHours] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (workTime) {
      setDays(String(workTime.work_days_per_year))
      setHours(String(workTime.work_hours_per_day))
    }
  }, [workTime])

  const handleSave = async () => {
    const workDays = parseInt(days, 10)
    const workHours = parseFloat(hours.replace(",", "."))
    if (!(workDays >= 1 && workDays <= 366) || !(workHours > 0 && workHours <= 24)) {
      toast.error("Jours entre 1 et 366, heures entre 0 et 24")
      return
    }
    setSaving(true)
    try {
      await api.patch<WorkTime>("/salary/work-time", { work_days_per_year: workDays, work_hours_per_day: workHours })
      await refresh()
      toast.success("Temps de travail enregistré")
    } catch (error) {
      toast.error("Impossible d'enregistrer le temps de travail")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Prix en heures de travail
        </CardTitle>
        <CardDescription>
          Convertit vos dépenses en temps de travail : salaire net × 12 ÷ (jours travaillés × heures par jour).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-end">
          <div className="space-y-2">
            <Label>Jours travaillés par an</Label>
            <Input type="number" min={1} max={366} value={days} onChange={e => setDays(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Heures par jour</Label>
            <Input type="number" min={0.5} max={24} step="0.5" value={hours} onChange={e => setHours(e.target.value)} />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Taux horaire net</p>
            {workTime?.hourly_rate ? (
              <p className="text-2xl font-black amount-blur">{formatCurrency(workTime.hourly_rate)}<span className="text-sm font-medium text-muted-foreground"> /h</span></p>
            ) : (
              <p className="text-sm text-muted-foreground">Configurez d'abord votre salaire.</p>
            )}
          </div>
          <Button onClick={handleSave} disabled={saving || !workTime}>
            {saving ? "Enregistrement..." : <><Save className="mr-2 h-4 w-4" /> Enregistrer</>}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
