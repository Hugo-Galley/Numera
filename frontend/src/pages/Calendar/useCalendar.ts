
import { useCalendarData } from "./useCalendarData"

/** Assemble l'état, les chargements et les actions de Calendar. */
export function useCalendar(embedded: boolean) {
  const calendarData = useCalendarData()
  return { embedded, ...calendarData }
}

export type CalendarCtx = ReturnType<typeof useCalendar>
