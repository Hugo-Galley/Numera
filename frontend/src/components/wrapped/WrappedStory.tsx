import { ChevronLeft, ChevronRight, X } from "lucide-react"
import { type WrappedReport } from "@/types/wrapped"
import { cn } from "@/lib/utils"
import { useCallback, useEffect, useMemo, useState } from "react"
import { useWorkTime } from "@/providers/WorkTimeProvider"
import { buildSlides } from "./wrappedSlides"

interface WrappedStoryProps {
  report: WrappedReport
  onClose: () => void
}

/** Bilan en plein écran, une carte par chiffre clé (clic, flèches du clavier, Échap pour fermer). */
export function WrappedStory({ report, onClose }: WrappedStoryProps) {
  const { workTime } = useWorkTime()
  const slides = useMemo(() => buildSlides(report, workTime?.work_hours_per_day ?? 7), [report, workTime])
  const [index, setIndex] = useState(0)
  const last = slides.length - 1

  const next = useCallback(() => {
    if (index >= last) onClose()
    else setIndex((i) => i + 1)
  }, [index, last, onClose])
  const prev = useCallback(() => setIndex((i) => Math.max(0, i - 1)), [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault()
        next()
      } else if (e.key === "ArrowLeft") prev()
      else if (e.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", onKey)
      document.body.style.overflow = ""
    }
  }, [next, prev, onClose])

  const slide = slides[index]

  return (
    <div className={cn("theme-island fixed inset-0 z-50 flex h-dvh flex-col overflow-hidden bg-gradient-to-br transition-colors duration-500", slide.tone)}>
      <div className="flex items-center gap-1.5 px-4 pt-[max(1rem,env(safe-area-inset-top))] sm:px-8">
        {slides.map((s, i) => (
          <button
            key={s.key}
            aria-label={`Carte ${i + 1}`}
            onClick={() => setIndex(i)}
            className={cn("relative h-1 flex-1 rounded-full transition-colors before:absolute before:-inset-y-3 before:inset-x-0 before:content-['']", i <= index ? "bg-white" : "bg-white/25")}
          />
        ))}
        <button onClick={onClose} aria-label="Fermer" className="-my-2 ml-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white/70 hover:bg-white/10 hover:text-white">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="relative flex flex-1 items-center justify-center overflow-y-auto overflow-x-hidden px-5 py-6 sm:px-6 sm:py-8">
        {/* Zones de navigation : tiers gauche = précédent, le reste = suivant */}
        <button aria-label="Précédent" onClick={prev} className="absolute inset-y-0 left-0 w-1/3 cursor-w-resize" />
        <button aria-label="Suivant" onClick={next} className="absolute inset-y-0 right-0 w-2/3 cursor-e-resize" />
        <div
          key={slide.key}
          className="pointer-events-none relative flex w-full max-w-2xl flex-col items-center gap-3 text-center wrapped-enter [&_.recharts-wrapper]:pointer-events-auto"
        >
          {slide.content}
        </div>
      </div>

      <div className="flex items-center justify-between px-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:px-8 sm:pb-6">
        <button onClick={prev} disabled={index === 0} className="flex h-12 w-12 items-center justify-center rounded-full text-white/70 hover:bg-white/10 disabled:opacity-0" aria-label="Précédent">
          <ChevronLeft className="h-6 w-6" />
        </button>
        <span className="text-xs font-semibold text-white/50">
          {index + 1} / {slides.length}
        </span>
        <button onClick={next} className="flex h-12 w-12 items-center justify-center rounded-full text-white/70 hover:bg-white/10" aria-label={index === last ? "Terminer" : "Suivant"}>
          <ChevronRight className="h-6 w-6" />
        </button>
      </div>
    </div>
  )
}
