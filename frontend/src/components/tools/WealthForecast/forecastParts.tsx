

export const HORIZONS = [5, 10, 20]

export function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="flex gap-3">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-blue-600">
        {n}
      </span>
      <div className="min-w-0 flex-1 space-y-3 text-sm text-slate-600">
        <p className="font-semibold text-slate-900">{title}</p>
        {children}
      </div>
    </section>
  )
}
export const EXTRA_PRESETS = [0, 50, 100, 200]
