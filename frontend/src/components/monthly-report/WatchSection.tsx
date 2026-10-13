import { AlertTriangle, CheckCircle2 } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import type { Insight } from "./types"

export function WatchSection({ insights }: { insights: Insight[] }) {
  const items = insights.filter((i) => i.type === "anomaly").slice(0, 5)
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-black text-slate-900">À regarder</h2>
      {items.length === 0 ? (
        <Card>
          <CardContent className="flex items-center gap-3 p-5 text-sm text-slate-500">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            Rien d'anormal ce mois-ci.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="divide-y divide-slate-100 p-0">
            {items.map((i, idx) => (
              <div key={idx} className="flex items-start gap-3 px-5 py-3">
                <AlertTriangle
                  className={`mt-0.5 h-4 w-4 shrink-0 ${i.severity === "high" ? "text-rose-500" : "text-amber-500"}`}
                />
                <div>
                  <div className="text-sm font-semibold text-slate-800">{i.title}</div>
                  <p className="amount-blur text-xs text-slate-500">{i.description}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </section>
  )
}
