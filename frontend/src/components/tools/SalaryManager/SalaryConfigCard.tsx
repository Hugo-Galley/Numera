import { Building, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { SalaryManagerCtx } from "./useSalaryManager"

/** Carte de configuration du salaire. */
export function SalaryConfigCard({ ctx }: { ctx: SalaryManagerCtx }) {
  const { accounts, categories, config, handleSaveConfig, saving, setConfig } = ctx
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building className="h-5 w-5" />
            Configuration Salaire & Avantages
          </CardTitle>
          <CardDescription>
            Définissez votre salaire net après primes et les comptes cibles pour automatiser vos transactions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-6">
            <div className="space-y-2">
              <Label>Salaire net après primes (€)</Label>
              <Input 
                type="number" inputMode="decimal" className="h-11 text-base md:h-9 md:text-sm" 
                value={config.net_salary} 
                onChange={e => setConfig({...config, net_salary: parseFloat(e.target.value) || 0})}
              />
            </div>
            <div className="space-y-2">
              <Label>Valeur ticket restaurant (€)</Label>
              <Input 
                type="number" inputMode="decimal" className="h-11 text-base md:h-9 md:text-sm" 
                step="0.01"
                value={config.ticket_value} 
                onChange={e => setConfig({...config, ticket_value: parseFloat(e.target.value) || 0})}
              />
            </div>
            <div className="space-y-2">
              <Label>Part salarié TR (€)</Label>
              <Input 
                type="number" inputMode="decimal" className="h-11 text-base md:h-9 md:text-sm" 
                step="0.01"
                value={config.ticket_employee_share} 
                onChange={e => setConfig({...config, ticket_employee_share: parseFloat(e.target.value) || 0})}
              />
            </div>

            <div className="space-y-2">
              <Label>Compte de versement Salaire *</Label>
              <Select value={config.salary_account_id.toString()} onValueChange={v => setConfig({...config, salary_account_id: Number(v)})}>
                <SelectTrigger className="h-11 md:h-9"><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {accounts.map(a => <SelectItem key={a.id} value={a.id.toString()}>{a.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Catégorie Salaire</Label>
              <Select value={config.salary_category_id ? config.salary_category_id.toString() : "none"} onValueChange={v => setConfig({...config, salary_category_id: v === "none" ? "" : parseInt(v)})}>
                <SelectTrigger className="h-11 md:h-9"><SelectValue placeholder="Aucune catégorie" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Aucune catégorie</SelectItem>
                  {categories.map(c => <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button onClick={handleSaveConfig} disabled={saving} className="h-11 w-full md:h-9">
                {saving ? "Enregistrement..." : <><Save className="mr-2 h-4 w-4" /> Sauvegarder</>}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
