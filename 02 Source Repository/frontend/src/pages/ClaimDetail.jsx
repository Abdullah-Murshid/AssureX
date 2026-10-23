import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { downloadReport, getClaim, getClaimHistory } from '../api/claims'
import { downloadDocument } from '../api/documents'
import { DecisionBadge, StatusBadge } from '../components/claims/ClaimBadges'
import ModelComparison from '../components/claims/ModelComparison'
import StatusTimeline from '../components/claims/StatusTimeline'
import OverrideModal from '../components/claims/OverrideModal'
import AuthedImage from '../components/ui/AuthedImage'
import Badge from '../components/ui/Badge'
import Button, { buttonClasses } from '../components/ui/Button'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import Icon from '../components/ui/Icon'
import Modal from '../components/ui/Modal'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { DOC_TYPE_LABEL } from '../lib/constants'
import { formatDate, formatDateTime, titleCase } from '../lib/format'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'

export default function ClaimDetail() {
  const { claimId } = useParams()
  const push = useToast((state) => state.push)
  const hasRole = useAuth((state) => state.hasRole)

  const [claim, setClaim] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [cardOpen, setCardOpen] = useState(false)

  const load = () => {
    setLoading(true)
    setError('')
    const request = getClaim(claimId)
      .then(setClaim)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
    getClaimHistory(claimId)
      .then((data) => setHistory(data.history || []))
      .catch(() => setHistory([]))
    return request
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claimId])

  if (loading && !claim) return <Spinner label="Loading claim dossier…" />
  if (error && !claim) {
    return (
      <Card>
        <EmptyState
          icon="alert"
          title="Claim unavailable"
          description={error}
          action={<Link to="/claims" className={buttonClasses({ size: 'sm' })}>Back to claims</Link>}
        />
      </Card>
    )
  }

  const dossier = claim.dossier || {}
  const comparison = dossier.comparison
  const explanation = dossier.explanation || {}
  const rules = dossier.rule_evaluation || {}
  const contradictions = dossier.contradictions?.contradictions || []
  const duplicates = dossier.duplicates?.duplicate_reasons || []
  const documents = claim.documents || []

  const download = (format) =>
    downloadReport(claim.claim_id, format).catch((err) => push(errorMessage(err), 'error'))

  return (
    <>
      <PageHeader
        eyebrow="Claim dossier"
        title={claim.claim_id}
        description={`${claim.product?.product_name || claim.product_id} · ${formatDate(claim.claim_submission_date)}`}
        actions={
          <>
            <Link to="/claims" className={buttonClasses({ variant: 'ghost', size: 'sm' })}>Back</Link>
            <Button variant="secondary" size="sm" icon="file" onClick={() => download('md')}>
              Markdown
            </Button>
            <Button variant="secondary" size="sm" icon="download" onClick={() => download('pdf')}>
              PDF report
            </Button>
            {hasRole('reviewer') && (
              <Button size="sm" icon="shield" onClick={() => setOverrideOpen(true)}>
                Review decision
              </Button>
            )}
          </>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <DecisionBadge decision={claim.final_decision} />
        <StatusBadge status={claim.status} />
        <Badge tone="neutral">Model {claim.model_version || '—'}</Badge>
        {claim.override_flag && <Badge tone="brand">Reviewer override</Badge>}
        {claim.consistency_status && <Badge tone={claim.consistency_status === 'Strong Match' ? 'success' : 'warning'}>{claim.consistency_status}</Badge>}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <ModelComparison comparison={comparison} />

          <Card>
            <CardHeader title="Decision rationale" subtitle={dossier.final_decision || claim.final_decision} />
            <CardBody className="grid gap-4 sm:grid-cols-2">
              <FactorList title="Supporting factors" items={explanation.supporting_factors} tone="success" icon="check" />
              <FactorList title="Opposing factors" items={explanation.opposing_factors} tone="danger" icon="alert" />
              {(explanation.required_actions || []).length > 0 && (
                <div className="sm:col-span-2">
                  <p className="mb-2 text-[11px] font-medium tracking-wide text-muted-light uppercase">Required actions</p>
                  <ul className="space-y-1.5 text-xs text-brand-500">
                    {explanation.required_actions.map((item, index) => (
                        <li key={`${item}-${index}`} className="flex gap-2">
                        <Icon name="chevronRight" size={13} className="mt-0.5 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Policy rule evaluation"
              subtitle={rules.category_policy}
              action={
                rules.hard_fail ? <Badge tone="danger">Hard fail</Badge> : <Badge tone="success">No hard fail</Badge>
              }
            />
            <CardBody className="space-y-4">
              {rules.failed_rules?.length > 0 && (
                <RuleGroup title="Failed rules" items={rules.failed_rules} tone="danger" />
              )}
              {rules.warnings?.length > 0 && <RuleGroup title="Warnings" items={rules.warnings} tone="warning" />}
              {rules.missing_documents?.length > 0 && (
                <RuleGroup title="Missing documents" items={rules.missing_documents} tone="danger" />
              )}
              <RuleGroup title="Passed rules" items={rules.passed_rules} tone="success" />
              {!rules.passed_rules?.length && !rules.failed_rules?.length && (
                <p className="text-xs text-muted-light">No rule evaluation recorded.</p>
              )}
            </CardBody>
          </Card>

          {(contradictions.length > 0 || duplicates.length > 0) && (
            <Card className="border-status-warning/25">
              <CardHeader title="Contradictions & duplicates" />
              <CardBody className="space-y-3 text-xs text-status-warning">
                {contradictions.map((item, index) => (
                  <p key={`${item}-${index}`} className="flex gap-2"><Icon name="alert" size={14} className="mt-0.5 shrink-0" />{item}</p>
                ))}
                {duplicates.map((item, index) => (
                  <p key={`${item}-${index}`} className="flex gap-2"><Icon name="refresh" size={14} className="mt-0.5 shrink-0" />{item}</p>
                ))}
              </CardBody>
            </Card>
          )}

          <Card>
            <CardHeader title="Evidence" subtitle={`${documents.length} document(s) attached`} />
            {documents.length === 0 ? (
              <EmptyState icon="file" title="No documents" description="This claim was submitted without attached evidence." />
            ) : (
              <Table minWidth="min-w-[560px]">
                <THead>
                  <tr>
                    <Th>Document</Th>
                    <Th>Type</Th>
                    <Th>Verified</Th>
                    <Th />
                  </tr>
                </THead>
                <TBody>
                  {documents.map((doc) => (
                    <tr key={doc.doc_id}>
                      <Td>
                        <p className="max-w-[220px] truncate text-ink">{doc.file_name}</p>
                        <p className="text-[11px] text-muted-light">{doc.doc_id}</p>
                      </Td>
                      <Td>{DOC_TYPE_LABEL[doc.file_type] || titleCase(doc.file_type)}</Td>
                      <Td>{doc.verified_at ? 'Yes' : 'Pending'}</Td>
                      <Td>
                        <Button
                          size="sm"
                          variant="ghost"
                          icon="download"
                          onClick={() => downloadDocument(doc.doc_id, doc.file_name).catch((err) => push(errorMessage(err), 'error'))}
                        >
                          Open
                        </Button>
                      </Td>
                    </tr>
                  ))}
                </TBody>
              </Table>
            )}
          </Card>

          <Card>
            <CardHeader title="Narrative summary" />
            <CardBody>
              <p className="text-sm leading-relaxed text-ink/80">{claim.narrative_summary || 'No narrative available.'}</p>
            </CardBody>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Claim summary card"
              subtitle="Rendered evidence card seen by the vision model"
              action={
                <Button size="sm" variant="ghost" icon="eye" onClick={() => setCardOpen(true)}>
                  Expand
                </Button>
              }
            />
            <CardBody>
              <AuthedImage path={`/claims/${claim.claim_id}/summary-card`} alt={`Summary card for ${claim.claim_id}`} className="w-full" />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Status timeline" subtitle={`${history.length} event(s)`} />
            <CardBody>
              <StatusTimeline history={history} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Claim metadata" />
            <CardBody>
              <dl className="space-y-2.5 text-xs">
                {[
                  ['Claim ID', claim.claim_id],
                  ['Status', claim.status],
                  ['Decision', claim.final_decision],
                  ['Fault', titleCase(claim.fault_category)],
                  ['Damage', titleCase(claim.damage_type)],
                  ['Occurred', formatDate(claim.fault_occurrence_date)],
                  ['Submitted', formatDate(claim.claim_submission_date)],
                  ['Created', formatDateTime(claim.created_at)],
                  ['Model version', claim.model_version || '—'],
                  ['Document hash', claim.document_hash ? `${claim.document_hash.slice(0, 16)}…` : '—'],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-start justify-between gap-4">
                    <dt className="text-muted-light">{label}</dt>
                    <dd className="max-w-[60%] text-right break-words text-ink">{value || '—'}</dd>
                  </div>
                ))}
              </dl>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Product" action={<Link to={`/products/${claim.product_id}`} className="text-xs text-brand-500 hover:text-brand-600">Open</Link>} />
            <CardBody className="space-y-1 text-xs">
              <p className="text-sm text-ink">{claim.product?.product_name || claim.product_id}</p>
              <p className="text-muted-light">{claim.product?.brand} · {claim.product?.model_number}</p>
              <p className="text-muted-light">Serial <span className="font-mono">{claim.product?.serial_number}</span></p>
              {claim.description && (
                <p className="mt-3 border-t border-line/70 pt-3 text-muted">{claim.description}</p>
              )}
            </CardBody>
          </Card>

          {(claim.reviewed_by || claim.reviewer_comments) && (
            <Card className="border-brand-500/20">
              <CardHeader title="Reviewer record" subtitle={claim.reviewed_by} />
              <CardBody className="text-xs text-ink/80">
                <p>{claim.reviewer_comments}</p>
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      <OverrideModal
        key={overrideOpen ? 'open' : 'closed'}
        claim={claim}
        open={overrideOpen}
        onClose={() => setOverrideOpen(false)}
        onDone={(updated) => {
          setOverrideOpen(false)
          setClaim((prev) => ({ ...prev, ...updated }))
          load()
        }}
      />

      <Modal open={cardOpen} onClose={() => setCardOpen(false)} title="Claim summary card" size="lg">
        <AuthedImage path={`/claims/${claim.claim_id}/summary-card`} alt={`Summary card for ${claim.claim_id}`} className="mx-auto max-w-md" />
      </Modal>
    </>
  )
}

function FactorList({ title, items, tone, icon }) {
  const styles =
    tone === 'success'
      ? 'border-status-success/25 bg-status-success/10 text-status-success'
      : 'border-status-danger/25 bg-status-danger/10 text-status-danger'
  return (
    <div>
      <p className="mb-2 text-[11px] font-medium tracking-wide text-muted-light uppercase">{title}</p>
      {items?.length ? (
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className={`flex gap-2 rounded-lg border px-3 py-2 text-xs ${styles}`}>
              <Icon name={icon} size={14} className="mt-0.5 shrink-0" />
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted-light">None recorded.</p>
      )}
    </div>
  )
}

function RuleGroup({ title, items, tone }) {
  const color =
    tone === 'success'
      ? 'border-status-success/25 bg-status-success/10 text-status-success'
      : tone === 'warning'
        ? 'border-status-warning/25 bg-status-warning/10 text-status-warning'
        : 'border-status-danger/25 bg-status-danger/10 text-status-danger'
  return (
    <div>
      <p className="mb-2 text-[11px] font-medium tracking-wide text-muted-light uppercase">{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, index) => (
          <span key={`${item}-${index}`} className={`rounded-lg border px-2.5 py-1 text-[11px] ${color}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}





