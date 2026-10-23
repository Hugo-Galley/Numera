import { useEffect, useRef, useState } from "react"
import { RefreshCw, WifiOff } from "lucide-react"

const PULL_THRESHOLD = 80

/** Bandeau hors-ligne + tirer pour actualiser (la PWA iOS n'offre pas ce geste en natif). */
export function PwaExtras({ scrollRef }: { scrollRef: React.RefObject<HTMLElement | null> }) {
  const [online, setOnline] = useState(() => navigator.onLine)
  const [pull, setPull] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const startY = useRef<number | null>(null)
  const pullRef = useRef(0)

  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener("online", update)
    window.addEventListener("offline", update)
    return () => {
      window.removeEventListener("online", update)
      window.removeEventListener("offline", update)
    }
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const isStandalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as any).standalone
    if (!isStandalone) return

    const onStart = (e: TouchEvent) => {
      // Pas pendant qu'une fenêtre modale est ouverte
      if (el.scrollTop <= 0 && !document.querySelector('[role="dialog"]')) startY.current = e.touches[0].clientY
    }
    const onMove = (e: TouchEvent) => {
      if (startY.current === null) return
      const delta = e.touches[0].clientY - startY.current
      if (delta <= 0 || el.scrollTop > 0) {
        pullRef.current = 0
        setPull(0)
        return
      }
      pullRef.current = Math.min(delta * 0.5, PULL_THRESHOLD + 20)
      setPull(pullRef.current)
    }
    const onEnd = () => {
      if (pullRef.current >= PULL_THRESHOLD) {
        setRefreshing(true)
        navigator.vibrate?.(10)
        window.location.reload()
      }
      startY.current = null
      pullRef.current = 0
      setPull(0)
    }
    el.addEventListener("touchstart", onStart, { passive: true })
    el.addEventListener("touchmove", onMove, { passive: true })
    el.addEventListener("touchend", onEnd)
    return () => {
      el.removeEventListener("touchstart", onStart)
      el.removeEventListener("touchmove", onMove)
      el.removeEventListener("touchend", onEnd)
    }
  }, [scrollRef])

  return (
    <>
      {!online && (
        <div className="fixed inset-x-0 top-[env(safe-area-inset-top)] z-[60] flex items-center justify-center gap-2 bg-amber-500 px-3 py-1 text-xs font-semibold text-white md:hidden" role="status">
          <WifiOff className="h-3.5 w-3.5" />
          Hors ligne — les données affichées peuvent être obsolètes
        </div>
      )}
      {(pull > 0 || refreshing) && (
        <div
          className="pointer-events-none fixed inset-x-0 z-[60] flex justify-center md:hidden"
          style={{ top: `calc(env(safe-area-inset-top) + 3.5rem + ${pull / 2}px)` }}
        >
          <div className="rounded-full bg-white p-2 shadow-lg ring-1 ring-slate-200">
            <RefreshCw className={`h-4 w-4 text-slate-700 ${refreshing ? "animate-spin" : ""}`} style={{ transform: `rotate(${pull * 3}deg)` }} />
          </div>
        </div>
      )}
    </>
  )
}
