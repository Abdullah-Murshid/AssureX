import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { dismissAlert, listAlerts } from '../api/warranties'
import { WarrantyBadge } from '../components/claims/ClaimBadges'
import Button, { buttonClasses } from '../components/ui/Button'
import Card, { CardBody } from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner, Tabs } from '../components/ui/Feedback'
import Icon from '../components/ui/Icon'
import Pagination from '../components/ui/Pagination'
import { formatDate, formatDays } from '../lib/format'
import { useToast } from '../store/toast'

const TABS = [
  { id: 'expiring', label: 'Expiring soon' },
  { id: 'grace', label: 'Grace period' },
  { id: 'expired', label: 'Expired' },
  { id: 'all', label: 'All alerts' },
]

export default function Alerts() {
  const push = useToast((state) => state.push)
  const [tab, setTab] = useState('expiring')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    listAlerts({ tab, page, per_page: 10 })
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, page])

  const dismiss = async (productId) => {
    try {
      await dismissAlert(productId)
      push(`Alert for ${productId} dismissed.`)
      load()
    } catch (err) {
      push(errorMessage(err), 'error')
    }
  }

  const summary = data?.summary || {}

  return (
    <>
      <PageHeader
        eyebrow="Coverage"
        title="Warranty alerts"
        description="Products whose coverage is expiring, in grace, or already expired."
      />

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        {[
          ['Expiring soon', summary.expiring_count, 'warning'],
          ['Grace period', summary.grace_count, 'info'],
          ['Expired', summary.expired_count, 'danger'],
        ].map(([label, value, tone]) => (
          <Card key={label}>
            <CardBody className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-light">{label}</p>
                <p className="mt-1 font-display text-[34px] leading-none text-ink">{value ?? 0}</p>
              </div>
              <span className={`rounded-xl border p-2 ${
                tone === 'warning'
                  ? 'border-status-warning/20 bg-status-warning/10 text-status-warning'
                  : tone === 'danger'
                    ? 'border-status-danger/20 bg-status-danger/10 text-status-danger'
                    : 'border-sky-500/20 bg-sky-500/10 text-brand-500'
              }`}>
                <Icon name="bell" size={18} />
              </span>
            </CardBody>
          </Card>
        ))}
      </div>

      <Tabs
        tabs={TABS}
        value={tab}
        onChange={(next) => {
          setTab(next)
          setPage(1)
        }}
        className="mb-4 w-fit"
      />

      {error && (
        <p className="mb-4 rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">
          {error}
        </p>
      )}

      <Card>
        {loading && !data ? (
          <Spinner label="Loading alerts…" />
        ) : data?.alerts?.length ? (
          <>
            <div className="divide-y divide-line/70">
              {data.alerts.map((alert) => (
                <div key={alert.product.product_id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                  <div className="min-w-0 flex-1">
                    <Link to={`/products/${alert.product.product_id}`} className="text-sm font-medium text-ink hover:text-brand-600">
                      {alert.product.product_name}
                    </Link>
                    <p className="text-[11px] text-muted-light">
                      {alert.product.brand} · <span className="font-mono">{alert.product.serial_number}</span>
                    </p>
                    <p className="mt-1 text-[11px] text-muted">
                      Expiry {formatDate(alert.warranty_expiry_date)} ·{' '}
                      {alert.remaining_warranty_days < 0
                        ? `${Math.abs(alert.remaining_warranty_days)} days overdue`
                        : `${formatDays(alert.remaining_warranty_days)} left`}
                    </p>
                  </div>
                  <WarrantyBadge status={alert.warranty_status} />
                  <div className="flex gap-2">
                    <Link to={`/claims/new?product=${alert.product.product_id}`} className={buttonClasses({ variant: 'secondary', size: 'sm' })}>
                      New claim
                    </Link>
                    <Button variant="ghost" size="sm" onClick={() => dismiss(alert.product.product_id)}>
                      Dismiss
                    </Button>
                  </div>
                </div>
              ))}
            </div>
            <Pagination
              page={data.pagination.page}
              totalPages={data.pagination.total_pages}
              total={data.pagination.total}
              onPage={setPage}
            />
          </>
        ) : (
          <EmptyState
            icon="bell"
            title="No alerts in this view"
            description="Coverage is healthy, or alerts have already been dismissed."
          />
        )}
      </Card>
    </>
  )
}


