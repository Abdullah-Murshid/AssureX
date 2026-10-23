import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { listNotifications, markAllNotificationsRead, markNotificationRead } from '../api/notifications'
import Card from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import Icon from '../components/ui/Icon'
import Pagination from '../components/ui/Pagination'
import { cn } from '../lib/cn'
import { formatDateTime } from '../lib/format'
import { useToast } from '../store/toast'

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

export default function Notifications() {
  const navigate = useNavigate()
  const push = useToast((state) => state.push)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    listNotifications({ unread: unreadOnly || undefined, page, per_page: 20 })
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unreadOnly, page])

  const openItem = async (item) => {
    if (!item.is_read) {
      try {
        await markNotificationRead(item.id)
        changed()
      } catch {
        /* still navigate */
      }
    }
    if (item.claim_id) navigate(`/claims/${item.claim_id}`)
    else if (item.product_id) navigate(`/products/${item.product_id}`)
  }

  const markAll = async () => {
    try {
      await markAllNotificationsRead()
      push('All notifications marked as read.', 'success')
      changed()
      load()
    } catch (err) {
      push(errorMessage(err), 'error')
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Notifications"
        description="Claim updates, review outcomes, document requests and warranty reminders."
        actions={
          <button
            type="button"
            onClick={markAll}
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-line bg-surface px-3 text-[12px] font-medium text-ink transition-colors hover:border-brand-500/40"
          >
            <Icon name="check" size={14} /> Mark all read
          </button>
        }
      />

      <div className="mb-4 flex items-center gap-2">
        {[
          ['All', false],
          ['Unread', true],
        ].map(([label, value]) => (
          <button
            key={label}
            type="button"
            onClick={() => {
              setPage(1)
              setUnreadOnly(value)
            }}
            className={cn(
              'rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors',
              unreadOnly === value
                ? 'border-brand-500 bg-tint text-brand-500'
                : 'border-line bg-surface text-muted hover:text-ink',
            )}
          >
            {label}
          </button>
        ))}
        {data && <span className="ml-auto text-[11px] text-muted-light">{data.unread} unread</span>}
      </div>

      <Card>
        {loading ? (
          <div className="p-10">
            <Spinner label="Loading notifications…" />
          </div>
        ) : error ? (
          <EmptyState icon="alert" title="Could not load notifications" description={error} />
        ) : !data?.items?.length ? (
          <EmptyState
            icon="bell"
            title={unreadOnly ? 'No unread notifications' : 'No notifications yet'}
            description={
              unreadOnly
                ? 'Everything here has been read.'
                : 'Claim and warranty updates will appear here.'
            }
          />
        ) : (
          <div>
            {data.items.map((item) => (
              <button
                type="button"
                key={item.id}
                onClick={() => openItem(item)}
                className={cn(
                  'flex w-full items-start gap-3 border-b border-line/60 px-4 py-4 text-left transition-colors last:border-0 hover:bg-surface-alt',
                  !item.is_read && 'bg-tint/40',
                )}
              >
                <span className={cn('mt-0.5', TONE[item.type] || 'text-muted')}>
                  <Icon name={ICON[item.type] || 'bell'} size={16} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-[13px] font-medium text-ink">{item.title}</span>
                    {!item.is_read && <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />}
                  </span>
                  <span className="mt-1 block text-[12px] text-muted">{item.message}</span>
                  <span className="mt-1.5 block text-[10.5px] text-muted-light">
                    {formatDateTime(item.created_at)}
                    {item.claim_id ? ` · ${item.claim_id}` : ''}
                  </span>
                </span>
              </button>
            ))}
            <div className="border-t border-line p-3">
              <Pagination
                page={data.page}
                totalPages={data.total_pages}
                total={data.total}
                onPage={setPage}
              />
            </div>
          </div>
        )}
      </Card>
    </>
  )
}
