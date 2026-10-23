import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { analytics as fetchAnalytics } from '../api/admin'
import { listClaims } from '../api/claims'
import { listProducts } from '../api/products'
import { reviewStats } from '../api/review'
import { listAlerts } from '../api/warranties'
import { DecisionBadge, StatusBadge, WarrantyBadge } from '../components/claims/ClaimBadges'
import { buttonClasses } from '../components/ui/Button'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import Icon from '../components/ui/Icon'
import StatCard from '../components/ui/StatCard'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { formatDate, initials, titleCase, truncate } from '../lib/format'
import { useAuth } from '../store/auth'

export default function Dashboard() {
  const user = useAuth((state) => state.user)
  const hasRole = useAuth((state) => state.hasRole)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    const tasks = [
      listClaims({ per_page: 100 }),
      listProducts({ per_page: 100 }),
      listAlerts({ tab: 'all' }),
      hasRole('reviewer') ? reviewStats() : Promise.resolve(null),
      hasRole('admin') ? fetchAnalytics() : Promise.resolve(null),
    ]

    Promise.allSettled(tasks).then((results) => {
      if (!active) return
      const value = (index, fallback) =>
        results[index].status === 'fulfilled' ? results[index].value : fallback
      setData({
        claims: value(0, { items: [] }),
        products: value(1, { items: [] }),
        alerts: value(2, { alerts: [], summary: {} }),
        review: value(3, null),
        analytics: value(4, null),
      })
      setLoading(false)
    })

    return () => {
      active = false
    }
  }, [hasRole])

  if (loading) return <Spinner label="Loading your workspace…" />

  const claims = data?.claims?.items || []
  const products = data?.products?.items || []
  const alerts = data?.alerts?.alerts || []
  const canIntake = hasRole('customer', 'service_center')
  const count = (decision) => claims.filter((claim) => claim.final_decision === decision).length
  const total = data?.claims?.total ?? claims.length

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title={`Welcome back, ${user?.full_name || 'there'}`}
        description="Your claims, coverage and adjudication activity at a glance."
        actions={
          canIntake ? (
            <>
              <Link to="/products/new" className={buttonClasses({ variant: 'secondary' })}>
                <Icon name="plus" size={15} /> Register product
              </Link>
              <Link to="/claims/new" className={buttonClasses({ variant: 'primary' })}>
                <Icon name="plus" size={15} /> New claim
              </Link>
            </>
          ) : (
            <Link to="/review" className={buttonClasses({ variant: 'primary' })}>
              <Icon name="shield" size={15} /> Open review queue
            </Link>
          )
        }
      />

      <div className="grid min-w-0 animate-enter-up gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total claims" value={total} hint="All submitted claims" icon="clipboard" />
        <StatCard
          label="Likely valid"
          value={count('Likely Valid')}
          hint="Auto-approval candidates"
          icon="check"
          tone="success"
        />
        <StatCard
          label="Needs review"
          value={count('Manual Review Required')}
          hint="Manual adjudication required"
          icon="shield"
          tone="warning"
        />
        <StatCard
          label="Covered products"
          value={data?.products?.total ?? products.length}
          hint="Registered under your account"
          icon="box"
          tone="neutral"
        />
      </div>

      <div className="mt-6 grid gap-6 2xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="min-w-0">
          <CardHeader
            title="Recent claims"
            subtitle="Latest submissions and adjudication outcomes"
            action={
              <Link to="/claims" className="text-xs font-medium text-brand-500 hover:text-brand-600">
                View all
              </Link>
            }
          />
          {claims.length === 0 ? (
            <EmptyState
              icon="clipboard"
              title="No claims yet"
              description="Submit your first warranty claim to see the dual-model decision here."
              action={
                <Link to="/claims/new" className={buttonClasses({ size: 'sm' })}>
                  New claim
                </Link>
              }
            />
          ) : (
            <Table minWidth="min-w-[850px]" className="table-fixed">
              <colgroup>
                <col className="w-[17%]" />
                <col className="w-[24%]" />
                <col className="w-[25%]" />
                <col className="w-[18%]" />
                <col className="w-[16%]" />
              </colgroup>
              <THead>
                <tr>
                  <Th className="px-5">Claim</Th>
                  <Th className="px-5">Product</Th>
                  <Th className="px-5">Decision</Th>
                  <Th className="px-5">Status</Th>
                  <Th className="px-5 pr-6 text-right">Submitted</Th>
                </tr>
              </THead>
              <TBody>
                {claims.slice(0, 8).map((claim, index) => (
                  <tr
                    key={claim.claim_id}
                    className="claim-row-enter h-[80px] transition-colors hover:bg-[#FAFAF8]"
                    style={{ animationDelay: `${index < 10 ? index * 50 : 500}ms` }}
                  >
                    <Td className="px-5 py-4">
                      <Link
                        to={`/claims/${claim.claim_id}`}
                        className="block truncate font-mono text-[12px] font-medium whitespace-nowrap text-brand-500 hover:text-brand-600"
                      >
                        {claim.claim_id}
                      </Link>
                      <p
                        className="mt-1 truncate text-[11px] text-muted-light"
                        title={titleCase(claim.fault_category)}
                      >
                        {titleCase(claim.fault_category)}
                      </p>
                    </Td>
                    <Td className="px-5 py-4">
                      <p
                        className="truncate text-ink"
                        title={claim.product?.product_name || '—'}
                      >
                        {claim.product?.product_name || '—'}
                      </p>
                      <p className="mt-1 truncate font-mono text-[11px] text-muted-light">
                        {claim.product?.serial_number}
                      </p>
                    </Td>
                    <Td className="px-5 py-4">
                      <DecisionBadge decision={claim.final_decision} />
                    </Td>
                    <Td className="px-5 py-4">
                      <StatusBadge status={claim.status} />
                    </Td>
                    <Td className="px-5 py-4 pr-6 text-right whitespace-nowrap text-muted">
                      {formatDate(claim.claim_submission_date)}
                    </Td>
                  </tr>
                ))}
              </TBody>
            </Table>
          )}
        </Card>

        <div className="min-w-0 space-y-6">
          <Card>
            <CardHeader
              title="Warranty alerts"
              subtitle={`${data?.alerts?.summary?.total_all ?? 0} product(s) need attention`}
              action={
                <Link to="/alerts" className="text-xs font-medium text-brand-500 hover:text-brand-600">
                  All
                </Link>
              }
            />
            <CardBody className="space-y-3">
              {alerts.length === 0 ? (
                <p className="py-6 text-center text-xs text-muted-light">No expiring or expired warranties.</p>
              ) : (
                alerts.slice(0, 4).map((alert) => (
                  <Link
                    key={alert.product.product_id}
                    to={`/products/${alert.product.product_id}`}
                    className="flex items-center justify-between gap-2 rounded-xl border border-line/70 bg-[#FAFAF8] px-3 py-2.5 transition-colors hover:border-brand-500/30"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-xs font-medium text-ink">{alert.product.product_name}</p>
                      <p className="text-[11px] text-muted-light">
                        {alert.remaining_warranty_days < 0
                          ? `${Math.abs(alert.remaining_warranty_days)} days past expiry`
                          : `${alert.remaining_warranty_days} days remaining`}
                      </p>
                    </div>
                    <WarrantyBadge status={alert.warranty_status} />
                  </Link>
                ))
              )}
            </CardBody>
          </Card>

          {hasRole('reviewer') && data?.review && (
            <Card>
              <CardHeader title="Review queue" subtitle="Claims awaiting a human decision" />
              <CardBody className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted">Manual review</span>
                  <span className="text-lg font-semibold text-status-warning">{data.review.manual_review}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted">Request more info</span>
                  <span className="font-medium text-ink">{data.review.request_more_info}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted">Overrides recorded</span>
                  <span className="font-medium text-ink">{data.review.overrides}</span>
                </div>
                <Link to="/review" className={buttonClasses({ variant: 'secondary', size: 'sm', className: 'w-full' })}>
                  Open queue
                </Link>
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="type-card-title">Covered products</h2>
          <Link to="/products" className="text-xs font-medium text-brand-500 hover:text-brand-600">
            View all
          </Link>
        </div>
        {products.length === 0 ? (
          <Card>
            <EmptyState
              icon="box"
              title="No products registered"
              description="Register a product to start submitting warranty claims."
              action={
                <Link to="/products/new" className={buttonClasses({ size: 'sm' })}>
                  Register product
                </Link>
              }
            />
          </Card>
        ) : (
          <div className="grid animate-enter-up gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {products.slice(0, 4).map((row) => (
              <Link
                key={row.product.product_id}
                to={`/products/${row.product.product_id}`}
                className="rounded-2xl border border-line bg-surface p-4 shadow-card-soft transition-colors hover:border-brand-500/30"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[10px] font-medium tracking-[0.12em] text-muted-light uppercase">
                    {titleCase(row.product.category)}
                  </span>
                  <WarrantyBadge status={row.warranty_status} />
                </div>
                <p className="type-card-title mt-3 truncate">{row.product.product_name}</p>
                <p className="text-[11px] text-muted-light">{row.product.brand} · {row.product.model_number}</p>
                <p className="mt-2 text-[11px] text-muted">
                  Expires {formatDate(row.warranty_expiry_date)}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>

      {data?.analytics?.monitoring?.flags?.length > 0 && (
        <Card className="mt-6 border-status-warning/25">
          <CardBody className="flex flex-wrap items-center gap-3 text-xs text-status-warning">
            <Icon name="alert" size={16} className="text-status-warning" />
            <span className="font-medium">Monitoring flags:</span>
            {data.analytics.monitoring.flags.join(' ')}
          </CardBody>
        </Card>
      )}

      <p className="mt-8 text-center text-[11px] text-muted-light">
        Signed in as {initials(user?.full_name)} · {truncate(user?.email, 40)}
      </p>
    </>
  )
}





