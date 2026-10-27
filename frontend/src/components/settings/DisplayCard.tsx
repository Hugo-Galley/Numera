import { Layers } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { useUI } from "@/providers/UIProvider"

export function DisplayCard() {
  const { hideHoldingValues, setHideHoldingValues } = useUI()

  return (
    <Card className="shadow-sm border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-slate-500" />
          <CardTitle className="text-lg">Affichage</CardTitle>
        </div>
        <CardDescription>Préférences d'affichage propres à ce navigateur.</CardDescription>
      </CardHeader>
      <CardContent className="p-4 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <Label htmlFor="hide-holding-values" className="font-bold text-slate-900 cursor-pointer">
              Positions simplifiées (comptes titres)
            </Label>
            <p className="text-sm text-slate-500">
              N'affiche que le titre (logo, nom, ticker) et le nombre de parts : PRU, cours, valeurs, plus-values, dividendes et poids sont masqués.
            </p>
          </div>
          <Switch
            id="hide-holding-values"
            checked={hideHoldingValues}
            onCheckedChange={setHideHoldingValues}
          />
        </div>
      </CardContent>
    </Card>
  )
}
