import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getUnreadCount, listNotifications, markAllNotificationsRead, markNotificationRead } from '../../api/notifications'
import { cn } from '../../lib/cn'
import { formatDate } from '../../lib/format'
import Icon from '../ui/Icon'

const TONE = {
  claim_approved: 'text-status-success',
  claim_rejected: 'text-status-danger',
  manual_review: 'text-status-warning',
  manual_review_assigned: 'text-status-warning',
  missing_documents: 'text-status-danger',
  additional_info_requested: 'text-status-warning',
  warranty_expiry: 'text-status-warning',
  review_completed: 'text-brand-500',
  claim_submitted: 'text-brand-500',
  claim_status: 'text-brand-500',
}

const ICON = {
  claim_approved: 'check',
  claim_rejected: 'alert',
  manual_review: 'shield',
  manual_review_assigned: 'shield',
  missing_documents: 'file',
  additional_info_requested: 'alert',
  warranty_expiry: 'clock',
  review_completed: 'check',
  claim_submitted: 'file',
}

const changed = () => window.dispatchEvent(new Event('assurex:notifications-changed'))

export default function NotificationBell() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [count, setCount] = useState(0)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const panelRef = useRef(null)

  useEffect(() => {
    let active = true
    const loadCount = () =>
      getUnreadCount()
        .then((data) => active && setCount(data.count || 0))
        .catch(() => {})
    loadCount()
    const timer = setInterval(loadCount, 45_000)
    const refresh = () => loadCount()
    window.addEventListener('assurex:notifications-changed', refresh)
    return () => {
      active = false
      clearInterval(timer)
      window.removeEventListener('assurex:notifications-changed', refresh)
    }
  }, [])

  useEffect(() => {
    if (!open) return undefined
    const close = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const loadLatest = () => {
    setLoading(true)
    listNotifications({ per_page: 6 })
      .then((data) => {
        setItems(data.items || [])
        setCount(data.unread ?? count)
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }

  const toggle = () => {
    const next = !open
    setOpen(next)
    if (next) loadLatest()
  }

  const openItem = async (item) => {
    if (!item.is_read) {
      try {
        await markNotificationRead(item.id)
        setItems((prev) => prev.map((row) => (row.id === item.id ? { ...row, is_read: true } : row)))
        setCount((value) => Math.max(0, value - 1))
        changed()
      } catch {
        /* the target page still opens */
      }
    }
    setOpen(false)
    if (item.claim_id) navigate(`/claims/${item.claim_id}`)
    else if (item.product_id) navigate(`/products/${item.product_id}`)
    else navigate('/notifications')
  }

  const markAll = async () => {
    try {
      await markAllNotificationsRead()
      setItems((prev) => prev.map((row) => ({ ...row, is_read: true })))
      setCount(0)
      changed()
    } catch {
      /* ignored */
    }
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={toggle}
        className="relative flex h-8 w-8 items-center justify-center rounded-full border border-line bg-surface text-muted transition-colors hover:border-brand-500/40 hover:text-ink"
        title="Notifications"
        aria-label="Notifications"
        aria-expanded={open}
      >
        <Icon name="bell" size={15} />
        {count > 0 && (
          <span className="absolute -right-1 -top-1 flex min-w-[15px] items-center justify-center rounded-full bg-status-danger px-1 text-[9px] font-semibold leading-4 text-white">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-50 w-[360px] overflow-hidden rounded-xl border border-line bg-surface shadow-card">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <p className="text-[13px] font-semibold text-ink">Notifications</p>
            <button
              type="button"
              onClick={markAll}
              className="text-[11px] font-medium text-brand-500 hover:text-brand-600"
            >
              Mark all read
            </button>
          </div>

          <div className="max-h-[390px] overflow-y-auto">
            {loading && <p className="px-4 py-6 text-center text-xs text-muted-light">Loading…</p>}
            {!loading && items.length === 0 && (
              <p className="px-4 py-8 text-center text-xs text-muted-light">You’re all caught up.</p>
            )}
            {!loading &&
              items.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => openItem(item)}
                  className={cn(
                    'flex w-full items-start gap-3 border-b border-line/60 px-4 py-3 text-left transition-colors last:border-0 hover:bg-surface-alt',
                    !item.is_read && 'bg-tint/40',
                  )}
                >
                  <span className={cn('mt-0.5', TONE[item.type] || 'text-muted')}>
                    <Icon name={ICON[item.type] || 'bell'} size={15} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="truncate text-[12px] font-medium text-ink">{item.title}</span>
                      {!item.is_read && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />}
                    </span>
                    <span className="mt-0.5 line-clamp-2 block text-[11px] text-muted">{item.message}</span>
                    <span className="mt-1 block text-[10px] text-muted-light">{formatDate(item.created_at)}</span>
                  </span>
                </button>
              ))}
          </div>

          <Link
            to="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-line px-4 py-3 text-center text-[11px] font-medium text-brand-500 hover:bg-surface-alt"
          >
            View all notifications
          </Link>
        </div>
      )}
    </div>
  )
}
