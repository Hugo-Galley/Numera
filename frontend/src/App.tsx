import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AppLayout } from "@/components/layout/AppLayout"
import Dashboard from "@/pages/Dashboard"
import Accounts from "@/pages/Accounts"
import AccountDetail from "@/pages/AccountDetail"
import Investments from "@/pages/Investments"
import Settings from "@/pages/Settings"
import Savings from "@/pages/Savings"
import Comparison from "@/pages/Comparison"
import IntelligentReport from "@/pages/MonthlyReport"
import Calendar from "@/pages/Calendar"
import RecurringTransactions from "@/pages/RecurringTransactions"
import Reimbursements from "@/pages/Reimbursements"
import MonthReview from "@/pages/MonthReview"
import Wrapped from "@/pages/Wrapped"
import Login from "@/pages/Login"
import Audit from "@/pages/Audit"
import Tools from "@/pages/Tools"
import Tax from "@/pages/Tax"
import { UIProvider } from "@/providers/UIProvider"
import { AuthProvider } from "@/providers/AuthProvider"
import { ConfirmProvider } from "@/providers/ConfirmProvider"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"

export function App() {
  return (
    <UIProvider>
      <AuthProvider>
        <ConfirmProvider>
        <BrowserRouter>
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
              <Route path="/comparison" element={<Comparison />} />
              <Route path="/report" element={<IntelligentReport />} />
              <Route path="/calendar" element={<Calendar />} />
              <Route path="/recurring" element={<RecurringTransactions />} />
              <Route path="/reimbursements" element={<Reimbursements />} />
              <Route path="/month-review" element={<MonthReview />} />
              <Route path="/wrapped" element={<Wrapped />} />
              <Route path="/audit" element={<Audit />} />
              <Route path="/tools" element={<Tools />} />
              <Route path="/tax" element={<Tax />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        </ConfirmProvider>
      </AuthProvider>
    </UIProvider>
  )
}
