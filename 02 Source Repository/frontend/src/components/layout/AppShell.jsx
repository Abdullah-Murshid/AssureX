import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { health } from '../../api/system'
import { NAV_ITEMS } from '../../lib/constants'
import { initials } from '../../lib/format'
import { cn } from '../../lib/cn'
import { useAuth } from '../../store/auth'
import NotificationBell from '../notifications/NotificationBell'
import Icon from '../ui/Icon'

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-[8px] bg-brand-500 font-sans text-[15px] font-semibold leading-none text-white">
        A
      </span>
      <span className="leading-tight">
        <span className="block text-[14px] font-semibold tracking-tight text-ink">AssureX</span>
        <span className="block text-[9px] tracking-[0.18em] text-muted-light uppercase">
          Claim Engine
        </span>
      </span>
    </Link>
  )
}

function ModelStatus() {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    let active = true
    const load = () =>
      health()
        .then((data) => active && setStatus(data))
        .catch(() => active && setStatus(null))
    load()
    const timer = setInterval(load, 60_000)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [])

  const ready = status?.models_ready
  return (
    <span
      title={
        ready
          ? `Models ready (loaded in ${status.load_seconds ?? '—'}s)`
          : 'AI models are still loading'
      }
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[4px] border px-2 py-[3px] text-[10px] font-medium tracking-[0.06em] uppercase',
        ready
          ? 'border-status-success/20 bg-status-success/[0.07] text-status-success'
          : 'border-status-warning/25 bg-status-warning/[0.08] text-status-warning',
      )}
    >
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          ready ? 'live-dot bg-status-success' : 'bg-status-warning',
        )}
      />
      {ready ? 'AI Online' : 'AI Loading'}
    </span>
  )
}

export default function AppShell() {
  const user = useAuth((state) => state.user)
  const hasRole = useAuth((state) => state.hasRole)
  const logout = useAuth((state) => state.logout)
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  const items = NAV_ITEMS.filter((item) => !item.roles || hasRole(item.roles))
  const current = items.find((item) =>
    item.end ? location.pathname === item.to : location.pathname.startsWith(item.to),
  )

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const sidebar = (
    <div className="flex h-full flex-col gap-6 p-4">
      <div className="px-1 pt-1">
        <Brand />
      </div>

      <nav className="flex-1 space-y-0.5">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors duration-200',
                isActive
                  ? 'bg-tint text-brand-500'
                  : 'text-muted hover:bg-surface-alt hover:text-ink',
              )
            }
          >
            <Icon name={item.icon} size={16} />
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="rounded-lg border border-line bg-[#FAFAF8] p-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-tint text-[11px] font-semibold text-brand-500">
            {initials(user?.full_name)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] font-medium text-ink">{user?.full_name}</p>
            <p className="text-[9.5px] tracking-[0.08em] text-muted-light uppercase">
              {user?.role?.replace('_', ' ')}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg p-1.5 text-muted-light transition-colors hover:bg-surface-alt hover:text-ink"
            title="Sign out"
          >
            <Icon name="logout" size={15} />
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-line bg-surface lg:block">
        {sidebar}
      </aside>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-[#0c1a14]/35 backdrop-blur-[2px]"
            onClick={() => setOpen(false)}
          />
          <aside className="relative h-full w-72 border-r border-line bg-surface">{sidebar}</aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 border-b border-line bg-background/90 backdrop-blur">
          <div className="flex h-16 items-center gap-3 px-4 lg:px-10">
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="rounded-lg p-2 text-muted hover:bg-surface-alt hover:text-ink lg:hidden"
              aria-label="Open navigation"
            >
              <Icon name="menu" size={18} />
            </button>
            <p className="text-[12px] font-medium tracking-[0.02em] text-muted">
              {location.pathname.startsWith('/notifications') ? 'Notifications' : current?.label || 'AssureX'}
            </p>
            <div className="ml-auto flex items-center gap-3">
              <NotificationBell />
              <ModelStatus />
              <Link
                to="/profile"
                className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-surface text-[11px] font-semibold text-ink transition-colors hover:border-brand-500/40"
                title="Profile"
              >
                {initials(user?.full_name)}
              </Link>
            </div>
          </div>
        </header>

        <main className="relative mx-auto w-full min-w-0 max-w-7xl px-4 py-7 lg:px-10 lg:py-9">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
