import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ChevronLeft, RefreshCw, WifiOff } from "lucide-react"

const PULL_THRESHOLD = 80
const EDGE_ZONE = 24
const SWIPE_BACK_DISTANCE = 70

/** Bandeau hors-ligne, tirer pour actualiser et balayage depuis le bord gauche = retour (la PWA iOS n'offre ni l'un ni l'autre en natif). */
export function PwaExtras({ scrollRef }: { scrollRef: React.RefObject<HTMLElement | null> }) {
  const [online, setOnline] = useState(() => navigator.onLine)
  const [pull, setPull] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [swipe, setSwipe] = useState(0)
  const navigate = useNavigate()
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

  useEffect(() => {
    const isStandalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as any).standalone
    if (!isStandalone) return
    let start: { x: number; y: number } | null = null
    let distance = 0

    const onStart = (e: TouchEvent) => {
      const t = e.touches[0]
      const canGoBack = (window.history.state?.idx ?? 0) > 0
      start = canGoBack && t.clientX <= EDGE_ZONE && !document.querySelector('[role="dialog"]') ? { x: t.clientX, y: t.clientY } : null
      distance = 0
    }
    const onMove = (e: TouchEvent) => {
      if (!start) return
      const t = e.touches[0]
      const dx = t.clientX - start.x
      if (Math.abs(t.clientY - start.y) > Math.abs(dx) && dx < 30) {
        start = null  // geste vertical : c'est un défilement
        setSwipe(0)
        return
      }
      distance = Math.max(0, dx)
      setSwipe(Math.min(distance, SWIPE_BACK_DISTANCE + 30))
    }
    const onEnd = () => {
      if (start && distance >= SWIPE_BACK_DISTANCE) {
        navigator.vibrate?.(10)
        navigate(-1)
      }
      start = null
      distance = 0
      setSwipe(0)
    }
    document.addEventListener("touchstart", onStart, { passive: true })
    document.addEventListener("touchmove", onMove, { passive: true })
    document.addEventListener("touchend", onEnd)
    document.addEventListener("touchcancel", onEnd)
    return () => {
      document.removeEventListener("touchstart", onStart)
      document.removeEventListener("touchmove", onMove)
      document.removeEventListener("touchend", onEnd)
      document.removeEventListener("touchcancel", onEnd)
    }
  }, [navigate])

  return (
    <>
      {swipe > 0 && (
        <div className="pointer-events-none fixed top-1/2 z-[60] -translate-y-1/2 md:hidden" style={{ left: swipe / 2 - 20 }}>
          <div className={`rounded-full p-2 shadow-lg ring-1 ring-slate-200 ${swipe >= SWIPE_BACK_DISTANCE ? "bg-slate-900 text-white" : "bg-white text-slate-700"}`}>
            <ChevronLeft className="h-5 w-5" />
          </div>
        </div>
      )}
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
