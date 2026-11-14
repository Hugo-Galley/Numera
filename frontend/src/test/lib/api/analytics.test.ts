import * as analytics from "@/lib/api/analytics"
import { BODY, describeApiCases } from "@/test/support/apiCases"
import { recordRequests } from "@/test/support/recordRequests"

const Q = "?month=6&year=2026"

describeApiCases("analytics", analytics, [
  { fn: "getAnalyticsAccountFlowSummary", args: [Q], method: "GET", path: "/analytics/account-flow-summary", query: Q },
  { fn: "getAnalyticsActions", method: "GET", path: "/analytics/actions" },
  { fn: "postAnalyticsActionsDismiss", args: [BODY], method: "POST", path: "/analytics/actions/dismiss", body: BODY },
  { fn: "getAnalyticsAssetAllocationSuggestions", method: "GET", path: "/analytics/asset-allocation/suggestions" },
  { fn: "getAnalyticsAuditById", args: [7], method: "GET", path: "/analytics/audit/7" },
  { fn: "getAnalyticsBudget", args: [Q], method: "GET", path: "/analytics/budget", query: Q },
  { fn: "getAnalyticsCalendar", args: [Q], method: "GET", path: "/analytics/calendar", query: Q },
  { fn: "getAnalyticsCashflowProjection", args: [Q], method: "GET", path: "/analytics/cashflow-projection", query: Q },
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
  { fn: "patchFinancialEventsById", args: [7, BODY], method: "PATCH", path: "/financial-events/7", body: BODY },
  { fn: "postFinancialEvents", args: [BODY], method: "POST", path: "/financial-events", body: BODY },
  { fn: "deleteFinancialEventsById", args: [7], method: "DELETE", path: "/financial-events/7" },
  { fn: "getFinancialEvents", method: "GET", path: "/financial-events" },
  { fn: "getAnalyticsDividends", args: ["?a=1"], method: "GET", path: "/analytics/dividends", query: "?a=1" },
  { fn: "getAnalyticsPortfolioById", args: [7], method: "GET", path: "/analytics/portfolio/7" },
  { fn: "getAnalyticsBudgetPeriod", args: ["?a=1"], method: "GET", path: "/analytics/budget-period", query: "?a=1" },
  { fn: "putAnalyticsBudgetPeriod", args: [BODY], method: "PUT", path: "/analytics/budget-period", body: BODY },
  { fn: "getAnalyticsFire", args: ["?a=1"], method: "GET", path: "/analytics/fire", query: "?a=1" },
  { fn: "getAnalyticsExpensesByCategory", args: ["?a=1"], method: "GET", path: "/analytics/expenses-by-category", query: "?a=1" },
  { fn: "getAnalyticsMonthlyReport", args: ["?a=1"], method: "GET", path: "/analytics/monthly-report", query: "?a=1" },
  { fn: "getAnalyticsBudgetAlerts", args: ["?a=1"], method: "GET", path: "/analytics/budget-alerts", query: "?a=1" },
  { fn: "getAnalyticsWrapped", args: ["?a=1"], method: "GET", path: "/analytics/wrapped", query: "?a=1" },
  { fn: "getAnalyticsInsights", args: ["?a=1"], method: "GET", path: "/analytics/insights", query: "?a=1" },
  { fn: "getAnalyticsPatrimoineAllocation", method: "GET", path: "/analytics/patrimoine-allocation" },
  { fn: "getAnalyticsSankey", args: ["?a=1"], method: "GET", path: "/analytics/sankey", query: "?a=1" },
  { fn: "getAnalyticsTopMerchants", args: ["?a=1"], method: "GET", path: "/analytics/top-merchants", query: "?a=1" },
])

describe("lib/api/analytics : query facultative", () => {
  it("sans query, l'URL reste nue", async () => {
    const requests = recordRequests()

    await analytics.getAnalyticsBudget()

    expect(requests[0]).toMatchObject({ path: "/analytics/budget", search: "" })
  })
})
