import { ArrowRight, Wrench, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { actionIconClass, actionTypeIcon, sampleLabel, severityClass, severityLabel } from "./types"
import type { AuditCtx } from "./useAudit"

/** Liste des actions à traiter. */
export function ActionList({ ctx }: { ctx: AuditCtx }) {
  const { dismissAction, handleAction } = ctx
  const data = ctx.data!
  return (
    <>
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
        <div className="divide-y divide-slate-100">
          {data.actions.map((action) => {
            const Icon = actionTypeIcon[action.type] || Wrench

            return (
              <div 
                key={action.id} 
                className="group flex cursor-pointer flex-col gap-4 p-4 transition-colors hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
                onClick={() => handleAction(action)}
              >
                <div className="flex min-w-0 items-start gap-3">
                  <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", actionIconClass[action.severity])} />
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <h2 className="text-sm font-semibold text-slate-900">{action.title}</h2>
                      <Badge variant="outline" className={cn("h-5 px-1.5 text-[9px] font-medium uppercase tracking-wider", severityClass[action.severity])}>
                        {severityLabel[action.severity]}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500 line-clamp-2 sm:line-clamp-1">{action.description}</p>
                  </div>
                </div>
                <div className="flex w-full shrink-0 items-center gap-2 sm:w-auto sm:gap-3">
                  {action.samples.length > 0 && (
                    <div className="hidden gap-2 sm:flex">
                      {action.samples.slice(0, 1).map((sample, index) => (
                        <span key={index} className="max-w-[150px] truncate text-xs text-slate-400">
                          Ex: {sampleLabel(sample)}
                        </span>
                      ))}
                    </div>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-11 flex-1 justify-center bg-slate-100 text-xs font-medium group-hover:bg-slate-200/50 sm:h-8 sm:flex-none sm:bg-transparent"
                  >
                    {action.action_label || "Traiter"}
                    <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-11 w-11 text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors sm:h-8 sm:w-8"
                    onClick={(e) => dismissAction(e, action.id)}
                    title="Masquer cette action définitivement"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}
