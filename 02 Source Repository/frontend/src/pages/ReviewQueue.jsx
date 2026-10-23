import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { reviewQueue, reviewStats } from '../api/review'
import { DecisionBadge, StatusBadge } from '../components/claims/ClaimBadges'
import OverrideModal from '../components/claims/OverrideModal'
import Button, { buttonClasses } from '../components/ui/Button'
import Card from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import Pagination from '../components/ui/Pagination'
import StatCard from '../components/ui/StatCard'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { formatDate, formatPercent, titleCase } from '../lib/format'

export default function ReviewQueue() {
  const [queue, setQueue] = useState(null)
  const [stats, setStats] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  const load = () => {
    setLoading(true)
    setError('')
    Promise.all([reviewQueue({ page, per_page: 12 }), reviewStats()])
      .then(([queueData, statsData]) => {
        setQueue(queueData)
        setStats(statsData)
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  return (
    <>
      <PageHeader
        eyebrow="Human in the loop"
        title="Review queue"
        description="Claims the engine escalated for a human disposition."
      />

      <div className="grid animate-enter-up gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Manual review" value={stats?.manual_review ?? '—'} icon="shield" tone="warning" hint="Awaiting decision" />
        <StatCard label="More info" value={stats?.request_more_info ?? '—'} icon="file" tone="neutral" hint="Waiting on the claimant" />
        <StatCard label="Overrides" value={stats?.overrides ?? '—'} icon="check" tone="success" hint="Recorded human decisions" />
        <StatCard label="Total claims" value={stats?.total_claims ?? '—'} icon="clipboard" tone="brand" hint="All claims in the system" />
      </div>

      {error && (
        <p className="mt-4 rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">
          {error}
        </p>
      )}

      <Card className="mt-6">
        {loading && !queue ? (
          <Spinner label="Loading review queue…" />
        ) : queue?.items?.length ? (
          <>
            <Table minWidth="min-w-[900px]">
              <THead>
                <tr>
                  <Th>Claim</Th>
                  <Th>Product</Th>
                  <Th>Decision</Th>
                  <Th>Status</Th>
                  <Th>Confidence</Th>
                  <Th>Submitted</Th>
                  <Th className="text-right">Action</Th>
                </tr>
              </THead>
              <TBody>
                {queue.items.map((claim) => (
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
                    <Td className="text-ink/80">
                      {formatPercent(claim.python_top_confidence)} / {formatPercent(claim.vision_top_confidence)}
                    </Td>
                    <Td className="whitespace-nowrap">{formatDate(claim.claim_submission_date)}</Td>
                    <Td>
                      <div className="flex justify-end gap-2">
                        <Link to={`/claims/${claim.claim_id}`} className={buttonClasses({ variant: 'ghost', size: 'sm' })}>
                          Dossier
                        </Link>
                        <Button size="sm" onClick={() => setSelected(claim)}>Decide</Button>
                      </div>
                    </Td>
                  </tr>
                ))}
              </TBody>
            </Table>
            <Pagination page={queue.page} totalPages={queue.total_pages} total={queue.total} onPage={setPage} />
          </>
        ) : (
          <EmptyState
            icon="check"
            title="Queue is clear"
            description="No claims are waiting for a manual disposition right now."
            action={<Link to="/claims" className={buttonClasses({ size: 'sm' })}>Browse claims</Link>}
          />
        )}
      </Card>

      <OverrideModal
        key={`${selected?.claim_id || 'none'}-${Boolean(selected)}`}
        claim={selected}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        onDone={() => {
          setSelected(null)
          load()
        }}
      />
    </>
  )
}



