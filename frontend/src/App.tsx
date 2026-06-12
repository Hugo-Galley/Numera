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
import Login from "@/pages/Login"
import Audit from "@/pages/Audit"
import { UIProvider } from "@/providers/UIProvider"
import { AuthProvider } from "@/providers/AuthProvider"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"

export function App() {
  return (
    <UIProvider>
      <AuthProvider>
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
              <Route path="/audit" element={<Audit />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </UIProvider>
  )
}
