import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AppLayout } from "@/components/layout/AppLayout"
import { UIProvider } from "@/providers/UIProvider"
import { AuthProvider } from "@/providers/AuthProvider"
import { ConfirmProvider } from "@/providers/ConfirmProvider"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"
import { PageLoader } from "@/components/layout/PageLoader"
import { ErrorBoundary } from "@/components/layout/ErrorBoundary"
import { RedirectKeepingSearch } from "@/components/layout/RedirectKeepingSearch"

// Une page = un fichier JS chargé à la demande (le bundle unique pesait 1,7 Mo)
const Dashboard = lazy(() => import("@/pages/Dashboard"))
const Accounts = lazy(() => import("@/pages/Accounts"))
const AccountDetail = lazy(() => import("@/pages/AccountDetail"))
const Investments = lazy(() => import("@/pages/Investments"))
const Settings = lazy(() => import("@/pages/Settings"))
const Classement = lazy(() => import("@/pages/Classement"))
const Savings = lazy(() => import("@/pages/Savings"))
const Comparison = lazy(() => import("@/pages/Comparison"))
const IntelligentReport = lazy(() => import("@/pages/MonthlyReport"))
const RecurringTransactions = lazy(() => import("@/pages/RecurringTransactions"))
const Reimbursements = lazy(() => import("@/pages/Reimbursements"))
const MonthReview = lazy(() => import("@/pages/MonthReview"))
const Wrapped = lazy(() => import("@/pages/Wrapped"))
const Login = lazy(() => import("@/pages/Login"))
const Audit = lazy(() => import("@/pages/Audit"))
const Tools = lazy(() => import("@/pages/Tools"))
const Tax = lazy(() => import("@/pages/Tax"))
const MonthHub = lazy(() => import("@/pages/MonthHub"))
const NotFound = lazy(() => import("@/pages/NotFound"))

export function App() {
  return (
    <ErrorBoundary fullPage>
    <UIProvider>
      <AuthProvider>
        <ConfirmProvider>
        <BrowserRouter>
          <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Dashboard />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/accounts/:id" element={<AccountDetail />} />
              <Route path="/savings" element={<Savings />} />
              <Route path="/investments" element={<Investments />} />
              <Route path="/month" element={<MonthHub />}>
                <Route index element={<Navigate to="bilan" replace />} />
                <Route path="bilan" element={<IntelligentReport />} />
                <Route path="revue" element={<MonthReview />} />
                <Route path="comparaison" element={<Comparison />} />
              </Route>
              <Route path="/recurring" element={<RecurringTransactions />} />
              <Route path="/reimbursements" element={<Reimbursements />} />
              {/* Anciennes adresses (favoris, liens internes) */}
              <Route path="/report" element={<RedirectKeepingSearch to="/month/bilan" />} />
              <Route path="/month-review" element={<RedirectKeepingSearch to="/month/revue" />} />
              <Route path="/comparison" element={<RedirectKeepingSearch to="/month/comparaison" />} />
              <Route path="/calendar" element={<RedirectKeepingSearch to="/recurring?tab=calendar" />} />
              <Route path="/wrapped" element={<Wrapped />} />
              <Route path="/audit" element={<Audit />} />
              <Route path="/tools" element={<Tools />} />
              <Route path="/tax" element={<Tax />} />
              <Route path="/classement" element={<Classement />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
          </Suspense>
        </BrowserRouter>
        </ConfirmProvider>
      </AuthProvider>
    </UIProvider>
    </ErrorBoundary>
  )
}
