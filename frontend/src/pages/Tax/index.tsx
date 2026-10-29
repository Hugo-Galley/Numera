import { Button } from "@/components/ui/button"
import { Settings2 } from "lucide-react"
import { useTax } from "./useTax"
import { TaxSettingsCard } from "./TaxSettingsCard"
import { AllocationAdviceCard } from "./AllocationAdviceCard"
import { WrappersSection } from "./WrappersSection"
import { AnnualReportSection } from "./AnnualReportSection"

export default function Tax() {
  const ctx = useTax()
  const { setSettingsOpen } = ctx
  return (
    <div className="space-y-6 md:space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between sm:gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Fiscalité</h1>
          <p className="text-sm text-muted-foreground md:text-base">Plafonds, dates clés et déclaration de tes enveloppes.</p>
        </div>
        <Button variant="outline" className="h-11 w-full sm:h-10 sm:w-auto" onClick={() => setSettingsOpen((open) => !open)}>
          <Settings2 className="mr-2 h-4 w-4" /> Réglages
        </Button>
      </div>

      <TaxSettingsCard ctx={ctx} />

      <AllocationAdviceCard ctx={ctx} />

      <WrappersSection ctx={ctx} />

      <AnnualReportSection ctx={ctx} />
    </div>
  )
}
