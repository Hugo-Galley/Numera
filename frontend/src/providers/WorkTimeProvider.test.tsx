import type { ReactNode } from "react"
import { act, renderHook, screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Toaster } from "@/components/ui/sonner"
import { apiUrl } from "@/test/handlers"
import { server } from "@/test/server"
import { makeToken } from "@/test/token"
import { useWorkTime, WorkTimeProvider, type WorkTime } from "./WorkTimeProvider"

const WORK_TIME: WorkTime = {
  configured: true,
  net_salary: 2500,
  work_days_per_year: 218,
  work_hours_per_day: 7,
  hours_per_month: 127.2,
  hourly_rate: 19.66,
}

const wrapper = ({ children }: { children: ReactNode }) => (
  <WorkTimeProvider>
    {children}
    <Toaster />
  </WorkTimeProvider>
)

beforeEach(() => window.localStorage.setItem("token", makeToken()))

describe("WorkTimeProvider", () => {
  it("charge /salary/work-time au montage avec le jeton", async () => {
    const auths: (string | null)[] = []
    server.use(
      http.get(apiUrl("/salary/work-time"), ({ request }) => {
        auths.push(request.headers.get("Authorization"))
        return HttpResponse.json(WORK_TIME)
      }),
    )

    const { result } = renderHook(() => useWorkTime(), { wrapper })

    expect(result.current.workTime).toBeNull()
    await waitFor(() => expect(result.current.workTime).toEqual(WORK_TIME))
    expect(auths).toEqual([expect.stringMatching(/^Bearer /)])
  })

  it("refresh recharge la valeur", async () => {
    let rate = 19.66
    server.use(http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ ...WORK_TIME, hourly_rate: rate })))
    const { result } = renderHook(() => useWorkTime(), { wrapper })
    await waitFor(() => expect(result.current.workTime?.hourly_rate).toBe(19.66))

    rate = 21
    await act(() => result.current.refresh())

    expect(result.current.workTime?.hourly_rate).toBe(21)
  })

  it("un échec affiche un toast et laisse workTime à null", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    server.use(http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))

    const { result } = renderHook(() => useWorkTime(), { wrapper })

    expect(await screen.findByText(/Impossible de charger le taux horaire/)).toBeInTheDocument()
    expect(result.current.workTime).toBeNull()
  })

  it("useWorkTime hors provider lève une erreur explicite", () => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    expect(() => renderHook(() => useWorkTime())).toThrow("useWorkTime must be used within a WorkTimeProvider")
  })
})
