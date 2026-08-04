import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/authContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Bills from './pages/Bills'
import Budgets from './pages/Budgets'
import Categories from './pages/Categories'
import CreditCards from './pages/CreditCards'
import Goals from './pages/Goals'
import Investments from './pages/Investments'
import Recurring from './pages/Recurring'
import Reports from './pages/Reports'
import Users from './pages/Users'

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAuthenticated, currentUser, authLoading } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  // Still resolving /api/auth/me — avoid a flash-redirect for an admin whose
  // role hasn't loaded yet.
  if (authLoading) {
    return null
  }
  if (!currentUser?.is_admin) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <RedirectIfAuthenticated>
            <Login />
          </RedirectIfAuthenticated>
        }
      />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/accounts"
        element={
          <RequireAuth>
            <Accounts />
          </RequireAuth>
        }
      />
      <Route
        path="/categories"
        element={
          <RequireAuth>
            <Categories />
          </RequireAuth>
        }
      />
      <Route
        path="/budgets"
        element={
          <RequireAuth>
            <Budgets />
          </RequireAuth>
        }
      />
      <Route
        path="/recurring"
        element={
          <RequireAuth>
            <Recurring />
          </RequireAuth>
        }
      />
      <Route
        path="/bills"
        element={
          <RequireAuth>
            <Bills />
          </RequireAuth>
        }
      />
      <Route
        path="/cards"
        element={
          <RequireAuth>
            <CreditCards />
          </RequireAuth>
        }
      />
      <Route
        path="/goals"
        element={
          <RequireAuth>
            <Goals />
          </RequireAuth>
        }
      />
      <Route
        path="/investments"
        element={
          <RequireAuth>
            <Investments />
          </RequireAuth>
        }
      />
      <Route
        path="/reports"
        element={
          <RequireAuth>
            <Reports />
          </RequireAuth>
        }
      />
      <Route
        path="/users"
        element={
          <RequireAdmin>
            <Users />
          </RequireAdmin>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
