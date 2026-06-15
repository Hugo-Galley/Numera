import { useState, useEffect } from "react"
import { format, getDaysInMonth, startOfMonth, getDay, isWeekend, addMonths, subMonths, isSameDay } from "date-fns"
import { fr } from "date-fns/locale"
import { ChevronLeft, ChevronRight, Home, Calendar as CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { cn } from "@/lib/utils"

interface TelecommutingCalendarProps {
  currentDate: Date
  onDateChange: (date: Date) => void
  salaryDate: Date | null
  onSalaryDateChange: (date: Date) => void
  ticketDate: Date | null
  onTicketDateChange: (date: Date) => void
  ttDays: Date[]
  onToggleDay: (date: Date) => void
}

export function TelecommutingCalendar({
  currentDate,
  onDateChange,
  salaryDate,
  onSalaryDateChange,
  ticketDate,
  onTicketDateChange,
  ttDays,
  onToggleDay
}: TelecommutingCalendarProps) {
  const daysInMonth = getDaysInMonth(currentDate)
  const firstDayOfMonth = startOfMonth(currentDate)
  const startingDayOfWeek = (getDay(firstDayOfMonth) + 6) % 7 // Lundi = 0

  const days = Array.from({ length: daysInMonth }, (_, i) => {
    const d = new Date(currentDate.getFullYear(), currentDate.getMonth(), i + 1)
    return d
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 border-b">
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <CalendarIcon className="h-5 w-5" />
          Calendrier Télétravail
        </CardTitle>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => onDateChange(subMonths(currentDate, 1))}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="w-32 text-center font-medium">
              {format(currentDate, "MMMM yyyy", { locale: fr })}
            </span>
            <Button variant="outline" size="icon" onClick={() => onDateChange(addMonths(currentDate, 1))}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-6 gap-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-full">
            <Home className="h-4 w-4 text-primary" />
            <span className="font-semibold text-foreground">{ttDays.length}</span> jours de TT = <span className="font-semibold text-foreground">{ttDays.length}</span> tickets
          </div>
          
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Versement Salaire:</span>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant={"outline"}
                    className={cn(
                      "w-[140px] justify-start text-left font-normal",
                      !salaryDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {salaryDate ? format(salaryDate, "dd/MM/yyyy") : <span>Choisir...</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={salaryDate || undefined}
                    onSelect={(d) => d && onSalaryDateChange(d)}
                    defaultMonth={currentDate}
                  />
                </PopoverContent>
              </Popover>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Versement TR:</span>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant={"outline"}
                    className={cn(
                      "w-[140px] justify-start text-left font-normal",
                      !ticketDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {ticketDate ? format(ticketDate, "dd/MM/yyyy") : <span>Choisir...</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={ticketDate || undefined}
                    onSelect={(d) => d && onTicketDateChange(d)}
                    defaultMonth={currentDate}
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-7 gap-1 md:gap-2 text-center">
          {['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'].map(day => (
            <div key={day} className="text-xs font-semibold text-muted-foreground mb-2">
              {day}
            </div>
          ))}
          
          {Array.from({ length: startingDayOfWeek }).map((_, i) => (
            <div key={`empty-${i}`} className="p-2" />
          ))}
          
          {days.map((date, i) => {
            const isWknd = isWeekend(date)
            const isTT = ttDays.some(d => isSameDay(d, date))
            
            return (
              <Button
                key={i}
                variant="outline"
                className={cn(
                  "h-12 md:h-16 flex flex-col items-center justify-center relative p-0 overflow-hidden",
                  isWknd ? "bg-muted/30 text-muted-foreground cursor-not-allowed opacity-50" : "hover:border-primary/50",
                  isTT && "bg-primary text-primary-foreground hover:bg-primary/90 hover:border-primary"
                )}
                disabled={isWknd}
                onClick={() => !isWknd && onToggleDay(date)}
              >
                <span className={cn(
                  "text-sm font-medium",
                  isTT && "text-primary-foreground"
                )}>
                  {format(date, 'd')}
                </span>
                {isTT && (
                  <Home className="h-4 w-4 absolute bottom-1 md:bottom-2 text-primary-foreground/80" />
                )}
              </Button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
