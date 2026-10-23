import { useEffect } from 'react'
import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'

import { REVIEWER_ROLES } from '../../lib/constants'
import { useAuth } from '../../store/auth'
import { buttonClasses } from '../ui/Button'
import { Spinner } from '../ui/Feedback'

export default function ProtectedRoute({ roles }) {
  const status = useAuth((state) => state.status)
  const hasRole = useAuth((state) => state.hasRole)
  const hydrate = useAuth((state) => state.hydrate)
  const location = useLocation()

  useEffect(() => {
    hydrate()
  }, [hydrate])

  if (status === 'idle' || status === 'loading') {
    return <Spinner label="Restoring your session…" className="min-h-screen" />
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (roles && !hasRole(roles)) {
    return (
      <div className="mx-auto flex max-w-lg flex-col items-center gap-4 py-24 text-center">
        <span className="rounded-2xl border border-status-danger/30 bg-status-danger/10 p-4 text-3xl">403</span>
        <h1 className="text-xl font-semibold text-ink">Access denied</h1>
        <p className="text-sm text-muted">
          Your role does not have permission to view this area. Reviewers and administrators only.
        </p>
        <Link to="/" className={buttonClasses({ variant: 'secondary' })}>
          Back to dashboard
        </Link>
      </div>
    )
  }

  return <Outlet />
}

export function RequireRole({ roles = REVIEWER_ROLES, children }) {
  const hasRole = useAuth((state) => state.hasRole)
  if (!hasRole(roles)) {
    return <Navigate to="/" replace />
  }
  return children
}

