import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import React from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Search } from "lucide-react"
import { useOmnibox } from "./useOmnibox"
import { NavAccountResults } from "./NavAccountResults"
import { QuickActionResults } from "./QuickActionResults"
import { TransactionResults } from "./TransactionResults"

export function Omnibox() {
  const ctx = useOmnibox()
  const { handleKeyDown, isSearchOpen, loading, query, scrollRef, setActiveIndex, setQuery, setSearchOpen, viewport } = ctx
  return (
    <Dialog open={isSearchOpen} onOpenChange={setSearchOpen}>
      <DialogContent 
        className="sm:max-w-[600px] p-0 gap-0 overflow-hidden border-none shadow-2xl rounded-2xl max-sm:left-0 max-sm:top-[var(--vvt,0px)] max-sm:flex max-sm:h-[var(--vvh,100dvh)] max-sm:max-h-none max-sm:w-full max-sm:max-w-none max-sm:translate-x-0 max-sm:translate-y-0 max-sm:flex-col max-sm:rounded-none max-sm:pt-[env(safe-area-inset-top)] max-sm:[&>button:last-child]:top-[calc(1rem+env(safe-area-inset-top))] max-sm:data-[state=closed]:slide-out-to-left-0 max-sm:data-[state=closed]:slide-out-to-top-0 max-sm:data-[state=open]:slide-in-from-left-0 max-sm:data-[state=open]:slide-in-from-top-0"
        style={viewport ? ({ "--vvh": `${viewport.height}px`, "--vvt": `${viewport.top}px` } as React.CSSProperties) : undefined}
        onKeyDown={handleKeyDown}
      >
        <DialogHeader className="px-4 py-3 pr-12 border-b flex flex-row items-center gap-3 shrink-0 sm:py-4 sm:pr-4">
          <DialogTitle className="sr-only">Recherche</DialogTitle>
          <DialogDescription className="sr-only">Rechercher un compte, une vue ou une transaction</DialogDescription>
          <Search className="h-5 w-5 text-slate-400 shrink-0" />
          <Input
            placeholder="Rechercher, ou saisir « 12,50 boulangerie »…"
            className="border-none shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-lg p-0 h-11 sm:h-10"
            inputMode="search"
            enterKeyHint="search"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="none"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActiveIndex(0)
            }}
            autoFocus
          />
          {loading && (
            <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}
        </DialogHeader>
        <ScrollArea className="min-h-0 flex-1 max-sm:[&>[data-radix-scroll-area-viewport]>div]:!block sm:max-h-[450px] sm:flex-none">
          <div className="p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]" ref={scrollRef}>
            <NavAccountResults ctx={ctx} />

            <QuickActionResults ctx={ctx} />

            <TransactionResults ctx={ctx} />
          </div>
        </ScrollArea>
        <div className="hidden shrink-0 px-4 py-3 border-t bg-slate-50 text-[10px] text-slate-400 justify-between items-center sm:flex">
          <div className="flex gap-4">
            <span className="flex items-center gap-1"><kbd className="bg-white border rounded px-1 text-slate-500 font-sans shadow-sm">↑↓</kbd> Naviguer</span>
            <span className="flex items-center gap-1"><kbd className="bg-white border rounded px-1 text-slate-500 font-sans shadow-sm">Enter</kbd> Sélectionner</span>
          </div>
          <div className="flex items-center gap-1">
            <kbd className="bg-white border rounded px-1 text-slate-500 font-sans shadow-sm">ESC</kbd> Fermer
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
