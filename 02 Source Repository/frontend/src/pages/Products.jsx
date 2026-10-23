import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { listProducts } from '../api/products'
import { WarrantyBadge } from '../components/claims/ClaimBadges'
import Button, { buttonClasses } from '../components/ui/Button'
import Card from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import { Input, Select } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import Pagination from '../components/ui/Pagination'
import { CATEGORIES, WARRANTY_STATUSES } from '../lib/constants'
import { formatDate, formatDays, titleCase } from '../lib/format'
import { useAuth } from '../store/auth'

export default function Products() {
  const hasRole = useAuth((state) => state.hasRole)
  const canIntake = hasRole('customer', 'service_center')
  const [filters, setFilters] = useState({ serial: '', category: '', warranty_status: '' })
  const [debouncedSerial, setDebouncedSerial] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSerial(filters.serial), 350)
    return () => clearTimeout(timer)
  }, [filters.serial])

  const query = useMemo(
    () => ({
      serial: debouncedSerial || undefined,
      category: filters.category || undefined,
      warranty_status: filters.warranty_status || undefined,
      page,
      per_page: 12,
    }),
    [debouncedSerial, filters.category, filters.warranty_status, page],
  )

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    listProducts(query)
      .then((result) => active && setData(result))
      .catch((err) => active && setError(errorMessage(err)))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [query])

  useEffect(() => {
    setPage(1)
  }, [debouncedSerial, filters.category, filters.warranty_status])

  return (
    <>
      <PageHeader
        eyebrow="Coverage"
        title="Products & warranties"
        description="Registered products, warranty windows and coverage policies."
        actions={
          canIntake ? (
            <Link to="/products/new" className={buttonClasses()}>
              <Icon name="plus" size={15} /> Register product
            </Link>
          ) : null
        }
      />

      <Card className="mb-5">
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            label="Serial number"
            placeholder="Search serial…"
            value={filters.serial}
            onChange={(event) => setFilters((prev) => ({ ...prev, serial: event.target.value }))}
          />
          <Select
            label="Category"
            value={filters.category}
            onChange={(event) => setFilters((prev) => ({ ...prev, category: event.target.value }))}
          >
            <option value="">All categories</option>
            {CATEGORIES.map((category) => (
              <option key={category.value} value={category.value}>
                {category.label}
              </option>
            ))}
          </Select>
          <Select
            label="Warranty status"
            value={filters.warranty_status}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, warranty_status: event.target.value }))
            }
          >
            <option value="">All statuses</option>
            {WARRANTY_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
          <div className="flex items-end">
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => setFilters({ serial: '', category: '', warranty_status: '' })}
            >
              Reset filters
            </Button>
          </div>
        </div>
      </Card>

      {error && (
        <p className="mb-4 rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">
          {error}
        </p>
      )}

      {loading && !data ? (
        <Spinner label="Loading products…" />
      ) : data?.items?.length ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.items.map((row) => (
              <Link
                key={row.product.product_id}
                to={`/products/${row.product.product_id}`}
                className="group rounded-2xl border border-line bg-surface p-5 shadow-card-soft transition-all hover:-translate-y-0.5 hover:border-brand-500/30"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-[10px] font-medium tracking-[0.12em] text-muted-light uppercase">
                    {titleCase(row.product.category)}
                  </span>
                  <WarrantyBadge status={row.warranty_status} />
                </div>
                <h3 className="type-card-title mt-3 truncate group-hover:text-brand-600">
                  {row.product.product_name}
                </h3>
                <p className="text-xs text-muted-light">
                  {row.product.brand} · {row.product.model_number}
                </p>

                <dl className="mt-4 grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <dt className="text-muted-light">Serial</dt>
                    <dd className="truncate font-mono text-[11px] text-ink/80">{row.product.serial_number}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-light">Category</dt>
                    <dd className="text-ink/80">{titleCase(row.product.category)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-light">Expiry</dt>
                    <dd className="text-ink/80">{formatDate(row.warranty_expiry_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-light">Remaining</dt>
                    <dd className="text-ink/80">{formatDays(row.remaining_warranty_days)}</dd>
                  </div>
                </dl>
              </Link>
            ))}
          </div>
          <Card className="mt-4">
            <Pagination
              page={data.page}
              totalPages={data.total_pages}
              total={data.total}
              onPage={setPage}
            />
          </Card>
        </>
      ) : (
        <Card>
          <EmptyState
            icon="box"
            title="No products found"
            description="Try adjusting the filters, or register a new product."
            action={
              canIntake ? (
                <Link to="/products/new" className={buttonClasses({ size: 'sm' })}>
                  Register product
                </Link>
              ) : null
            }
          />
        </Card>
      )}
    </>
  )
}


