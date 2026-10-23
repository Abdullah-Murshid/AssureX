import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { listClaims } from '../api/claims'
import { DecisionBadge, StatusBadge } from '../components/claims/ClaimBadges'
import Button, { buttonClasses } from '../components/ui/Button'
import Card from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import { Input, Select } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import Pagination from '../components/ui/Pagination'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { CLAIM_STATUSES } from '../lib/constants'
import { formatDate, formatPercent, titleCase } from '../lib/format'
import { useAuth } from '../store/auth'

const EMPTY_FILTERS = {
  claim_id: '',
  status: '',
  category: '',
  serial: '',
  date_from: '',
  date_to: '',
}

export default function Claims() {
  const hasRole = useAuth((state) => state.hasRole)
  const canIntake = hasRole('customer', 'service_center')
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [applied, setApplied] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const query = useMemo(
    () => ({
      claim_id: applied.claim_id || undefined,
      status: applied.status || undefined,
      category: applied.category || undefined,
      serial: applied.serial || undefined,
      date_from: applied.date_from || undefined,
      date_to: applied.date_to || undefined,
      page,
      per_page: 12,
    }),
    [applied, page],
  )

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    listClaims(query)
      .then((result) => active && setData(result))
      .catch((err) => active && setError(errorMessage(err)))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [query])

  const apply = (event) => {
    event.preventDefault()
    setPage(1)
    setApplied(filters)
  }

  const update = (key) => (event) => setFilters((prev) => ({ ...prev, [key]: event.target.value }))

  return (
    <>
      <PageHeader
        eyebrow="Adjudication"
        title="Claims"
        description="Every claim with its dual-model decision, consistency and reviewer status."
        actions={
          canIntake ? (
            <Link to="/claims/new" className={buttonClasses()}>
              <Icon name="plus" size={15} /> New claim
            </Link>
          ) : null
        }
      />

      <Card className="mb-5">
        <form onSubmit={apply} className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Input label="Claim ID" placeholder="CLM-2026-…" value={filters.claim_id} onChange={update('claim_id')} />
          <Select label="Status" value={filters.status} onChange={update('status')}>
            <option value="">All statuses</option>
            {CLAIM_STATUSES.map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </Select>
          <Input label="Serial" placeholder="Serial number" value={filters.serial} onChange={update('serial')} />
          <div className="grid grid-cols-2 gap-2">
            <Input label="From" type="date" value={filters.date_from} onChange={update('date_from')} />
            <Input label="To" type="date" value={filters.date_to} onChange={update('date_to')} />
          </div>
          <div className="flex items-end gap-2 lg:col-span-4">
            <Button type="submit" size="sm">Apply filters</Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setFilters(EMPTY_FILTERS)
                setApplied(EMPTY_FILTERS)
                setPage(1)
              }}
            >
              Clear
            </Button>
          </div>
        </form>
      </Card>

      {error && (
        <p className="mb-4 rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">
          {error}
        </p>
      )}

      <Card>
        {loading && !data ? (
          <Spinner label="Loading claims…" />
        ) : data?.items?.length ? (
          <>
            <Table minWidth="min-w-[860px]">
              <THead>
                <tr>
                  <Th>Claim</Th>
                  <Th>Product</Th>
                  <Th>Decision</Th>
                  <Th>Status</Th>
                  <Th>Python / Vision</Th>
                  <Th>Submitted</Th>
                  <Th />
                </tr>
              </THead>
              <TBody>
                {data.items.map((claim) => (
                  <tr key={claim.claim_id} className="transition-colors hover:bg-[#FAFAF8]">
                    <Td>
                      <Link to={`/claims/${claim.claim_id}`} className="font-mono text-[12px] font-medium whitespace-nowrap text-brand-500 hover:text-brand-600">
                        {claim.claim_id}
                      </Link>
                      <p className="text-[11px] text-muted-light">{titleCase(claim.fault_category)}</p>
                    </Td>
                    <Td>
                      <p className="text-ink">{claim.product?.product_name || claim.product_id}</p>
                      <p className="font-mono text-[11px] text-muted-light">{claim.product?.serial_number}</p>
                    </Td>
                    <Td>
                      <DecisionBadge decision={claim.final_decision} />
                      <p className="mt-1 text-[11px] text-muted-light">{claim.consistency_status}</p>
                    </Td>
                    <Td><StatusBadge status={claim.status} /></Td>
                    <Td>
                      <p className="text-ink/80">{claim.python_predicted_class}</p>
                      <p className="text-[11px] text-muted-light">
                        {formatPercent(claim.python_top_confidence)} / {formatPercent(claim.vision_top_confidence)}
                      </p>
                    </Td>
                    <Td className="whitespace-nowrap">{formatDate(claim.claim_submission_date)}</Td>
                    <Td>
                      <Link to={`/claims/${claim.claim_id}`} className="text-xs font-medium text-brand-500 hover:text-brand-600">
                        Open
                      </Link>
                    </Td>
                  </tr>
                ))}
              </TBody>
            </Table>
            <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onPage={setPage} />
          </>
        ) : (
          <EmptyState
            icon="clipboard"
            title="No claims found"
            description="Try different filters or submit a new claim."
            action={
              canIntake ? (
                <Link to="/claims/new" className={buttonClasses({ size: 'sm' })}>New claim</Link>
              ) : null
            }
          />
        )}
      </Card>

    </>
  )
}



