import React, { useState } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { Omnibox } from "./Omnibox"
import { Toaster } from "@/components/ui/sonner"
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Menu, CreditCard } from "lucide-react"

export function AppLayout() {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex h-screen w-full bg-slate-50/50 flex-col md:flex-row">
      {/* Mobile Header */}
      <header className="flex h-16 items-center border-b bg-white px-4 md:hidden shrink-0 justify-between">
        <div className="flex items-center">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="mr-2">
                <Menu className="h-6 w-6" />
                <span className="sr-only">Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="p-0 w-72">
              <SheetHeader className="sr-only">
                <SheetTitle>Navigation</SheetTitle>
                <SheetDescription>Menu de navigation mobile</SheetDescription>
              </SheetHeader>
              <Sidebar className="h-full border-none" onItemClick={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
          <CreditCard className="h-6 w-6 mr-2" />
          <span className="text-lg font-bold tracking-tight text-slate-900">Suivi Budget</span>
        </div>
      </header>

      {/* Desktop Sidebar */}
      <Sidebar className="hidden md:flex h-full w-64 border-r shrink-0" />

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="container mx-auto p-4 md:p-8 max-w-7xl">
          <Outlet />
        </div>
      </main>
      <Omnibox />
      <Toaster />
    </div>
  )
}
