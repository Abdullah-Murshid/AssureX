import { useEffect } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import AppShell from './components/layout/AppShell'
import ProtectedRoute from './components/layout/ProtectedRoute'
import { Toaster } from './components/ui/Feedback'
import { ADMIN_ROLES, INTAKE_ROLES, REVIEWER_ROLES } from './lib/constants'
import Admin from './pages/Admin'
import Alerts from './pages/Alerts'
import ClaimDetail from './pages/ClaimDetail'
import ClaimNew from './pages/ClaimNew'
import Claims from './pages/Claims'
import Dashboard from './pages/Dashboard'
import Documents from './pages/Documents'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Notifications from './pages/Notifications'
import ProductDetail from './pages/ProductDetail'
import ProductNew from './pages/ProductNew'
import Products from './pages/Products'
import Profile from './pages/Profile'
import Register from './pages/Register'
import Repairs from './pages/Repairs'
import ReviewQueue from './pages/ReviewQueue'
import { useAuth } from './store/auth'

export default function App() {
  useEffect(() => {
    const onUnauthorized = () => useAuth.getState().reset()
    window.addEventListener('assurex:unauthorized', onUnauthorized)
    return () => window.removeEventListener('assurex:unauthorized', onUnauthorized)
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route index element={<Dashboard />} />
            <Route path="products" element={<Products />} />
            <Route path="products/:productId" element={<ProductDetail />} />
            <Route path="documents" element={<Documents />} />
            <Route path="claims" element={<Claims />} />
            <Route path="claims/:claimId" element={<ClaimDetail />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="repairs" element={<Repairs />} />
            <Route path="profile" element={<Profile />} />

            <Route element={<ProtectedRoute roles={INTAKE_ROLES} />}>
              <Route path="products/new" element={<ProductNew />} />
              <Route path="claims/new" element={<ClaimNew />} />
            </Route>

            <Route element={<ProtectedRoute roles={REVIEWER_ROLES} />}>
              <Route path="review" element={<ReviewQueue />} />
            </Route>

            <Route element={<ProtectedRoute roles={ADMIN_ROLES} />}>
              <Route path="admin" element={<Admin />} />
            </Route>

            <Route path="*" element={<NotFound />} />
          </Route>
        </Route>
      </Routes>
      <Toaster />
    </BrowserRouter>
  )
}
