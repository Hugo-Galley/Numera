import * as analytics from "./analytics"
import { BODY, describeApiCases } from "@/test/apiCases"
import { recordRequests } from "@/test/recordRequests"

const Q = "?month=6&year=2026"

describeApiCases("analytics", analytics, [
  { fn: "getAnalyticsAccountFlowSummary", args: [Q], method: "GET", path: "/analytics/account-flow-summary", query: Q },
  { fn: "getAnalyticsActions", method: "GET", path: "/analytics/actions" },
  { fn: "postAnalyticsActionsDismiss", args: [BODY], method: "POST", path: "/analytics/actions/dismiss", body: BODY },
  { fn: "getAnalyticsAssetAllocationSuggestions", method: "GET", path: "/analytics/asset-allocation/suggestions" },
  { fn: "getAnalyticsAuditById", args: [7], method: "GET", path: "/analytics/audit/7" },
  { fn: "getAnalyticsBudget", args: [Q], method: "GET", path: "/analytics/budget", query: Q },
  { fn: "getAnalyticsCalendar", args: [Q], method: "GET", path: "/analytics/calendar", query: Q },
  { fn: "getAnalyticsDiversityScanner", method: "GET", path: "/analytics/diversity-scanner" },
  { fn: "getAnalyticsInvestmentsAllocation", method: "GET", path: "/analytics/investments-allocation" },
  { fn: "getAnalyticsInvestmentsAllocationAdvanced", method: "GET", path: "/analytics/investments-allocation-advanced" },
  { fn: "getAnalyticsInvestmentsById", args: [7], method: "GET", path: "/analytics/investments/7" },
  { fn: "getAnalyticsInvestmentsPerformanceHistory", args: [7], method: "GET", path: "/analytics/investments/7/performance-history" },
  { fn: "getAnalyticsKpiHistory", args: [Q], method: "GET", path: "/analytics/kpi-history", query: Q },
  { fn: "getAnalyticsResilience", args: [Q], method: "GET", path: "/analytics/resilience", query: Q },
  { fn: "getAnalyticsSubscriptions", args: [Q], method: "GET", path: "/analytics/subscriptions", query: Q },
  { fn: "postAnalyticsSubscriptionsIgnore", args: [BODY], method: "POST", path: "/analytics/subscriptions/ignore", body: BODY },
  { fn: "getAnalyticsTags", args: [Q], method: "GET", path: "/analytics/tags", query: Q },
  { fn: "getAnalyticsTimeseries", args: [Q], method: "GET", path: "/analytics/timeseries", query: Q },
  { fn: "getAnalyticsWealthForecast", args: [Q], method: "GET", path: "/analytics/wealth-forecast", query: Q },
  { fn: "getAnalyticsWealthSimulation", args: [Q], method: "GET", path: "/analytics/wealth-simulation", query: Q },
])

describe("lib/api/analytics : query facultative", () => {
  it("sans query, l'URL reste nue", async () => {
    const requests = recordRequests()

    await analytics.getAnalyticsBudget()

    expect(requests[0]).toMatchObject({ path: "/analytics/budget", search: "" })
  })
})
