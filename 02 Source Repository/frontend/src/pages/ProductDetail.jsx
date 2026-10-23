import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { downloadDocument, uploadDocument } from '../api/documents'
import { getProduct } from '../api/products'
import { createRepair } from '../api/repairs'
import { WarrantyBadge } from '../components/claims/ClaimBadges'
import Button, { buttonClasses } from '../components/ui/Button'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import { Checkbox, Input, Select, Textarea } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import Modal from '../components/ui/Modal'
import StatCard from '../components/ui/StatCard'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { DOC_TYPES, DOC_TYPE_LABEL } from '../lib/constants'
import { formatCurrency, formatDate, formatDays, titleCase } from '../lib/format'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'

const EMPTY_REPAIR = {
  repair_date: '',
  service_center_name: '',
  replaced_parts: '',
  repair_cost: '',
  outcome: '',
  authorized: true,
}

export default function ProductDetail() {
  const { productId } = useParams()
  const push = useToast((state) => state.push)
  const hasRole = useAuth((state) => state.hasRole)
  const canIntake = hasRole('customer', 'service_center')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [docOpen, setDocOpen] = useState(false)
  const [repairOpen, setRepairOpen] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    return getProduct(productId)
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [productId])

  useEffect(() => {
    load()
  }, [load])

  if (loading && !data) return <Spinner label="Loading product…" />
  if (error && !data) {
    return (
      <Card>
        <EmptyState icon="alert" title="Product unavailable" description={error} action={<Link to="/products" className={buttonClasses({ size: 'sm' })}>Back to products</Link>} />
      </Card>
    )
  }

  const product = data.product
  const policy = data.policy || {}
  const documents = data.documents || []
  const repairs = data.repairs || []
  const claims = data.claims || []

  return (
    <>
      <PageHeader
        eyebrow="Product"
        title={product.product_name}
        description={`${product.brand} · ${product.model_number} · Serial ${product.serial_number}`}
        actions={
          <>
            <Link to="/products" className={buttonClasses({ variant: 'ghost', size: 'sm' })}>
              Back
            </Link>
            {canIntake && (
              <>
                <Button variant="secondary" size="sm" icon="upload" onClick={() => setDocOpen(true)}>
                  Upload evidence
                </Button>
                <Button variant="secondary" size="sm" icon="wrench" onClick={() => setRepairOpen(true)}>
                  Log repair
                </Button>
                <Link to={`/claims/new?product=${product.product_id}`} className={buttonClasses({ size: 'sm' })}>
                  <Icon name="plus" size={14} /> New claim
                </Link>
              </>
            )}
          </>
        }
      />

      <div className="grid animate-enter-up gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Warranty" value={<WarrantyBadge status={data.warranty_status} />} hint={data.coverage_provider} icon="shield" tone={data.warranty_status === 'Active' ? 'success' : 'warning'} />
        <StatCard label="Expires" value={formatDate(data.warranty_expiry_date)} hint={`Started ${formatDate(data.warranty_start_date)}`} icon="clock" tone="neutral" />
        <StatCard label="Remaining" value={formatDays(data.remaining_warranty_days)} hint="Against the policy window" icon="trend" tone="brand" />
        <StatCard label="Purchase price" value={formatCurrency(product.purchase_price)} hint={product.retailer} icon="box" tone="neutral" />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card>
          <CardHeader title="Product information" />
          <CardBody>
            <dl className="space-y-2.5 text-xs">
              {[
                ['Product ID', product.product_id, true],
                ['Category', titleCase(product.category)],
                ['Brand', product.brand],
                ['Model', product.model_number],
                ['Serial', product.serial_number, true],
                ['Purchased', formatDate(product.purchase_date)],
                ['Retailer', product.retailer],
                ['Warranty duration', `${product.warranty_duration_months} months`],
                [
                  'Extended warranty',
                  product.has_extended_warranty
                    ? `${product.extended_warranty_provider || 'Yes'} ${product.extended_warranty_duration_months ? `(+${product.extended_warranty_duration_months} mo)` : ''}`
                    : 'None',
                ],
              ].map(([label, value, mono]) => (
                <div key={label} className="flex items-start justify-between gap-4">
                  <dt className="text-muted-light">{label}</dt>
                  <dd className={`text-right text-ink ${mono ? 'font-mono text-[11px]' : ''}`}>
                    {value || '—'}
                  </dd>
                </div>
              ))}
            </dl>
          </CardBody>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader title="Coverage policy" subtitle={policy.category_name || data.coverage_provider} />
          <CardBody className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-line/70 bg-[#FAFAF8] p-3">
                <p className="text-[11px] text-muted-light">Coverage</p>
                <p className="mt-1 text-sm text-ink">{policy.coverage_duration_months ?? '—'} months</p>
              </div>
              <div className="rounded-xl border border-line/70 bg-[#FAFAF8] p-3">
                <p className="text-[11px] text-muted-light">Grace period</p>
                <p className="mt-1 text-sm text-ink">{policy.grace_period_days ?? '—'} days</p>
              </div>
              <div className="rounded-xl border border-line/70 bg-[#FAFAF8] p-3">
                <p className="text-[11px] text-muted-light">Reporting deadline</p>
                <p className="mt-1 text-sm text-ink">{policy.reporting_deadline_days ?? '—'} days</p>
              </div>
            </div>

            <div>
              <p className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-light uppercase">Covered faults</p>
              <div className="flex flex-wrap gap-1.5">
                {(policy.covered_faults || []).map((fault, index) => (
                  <span key={`${fault}-${index}`} className="rounded-full border border-status-success/20 bg-status-success/10 px-2 py-0.5 text-[11px] text-status-success">
                    {titleCase(fault)}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-light uppercase">Exclusions</p>
              <div className="flex flex-wrap gap-1.5">
                {(policy.exclusions || []).map((item, index) => (
                  <span key={`${item}-${index}`} className="rounded-full border border-status-danger/20 bg-status-danger/10 px-2 py-0.5 text-[11px] text-status-danger">
                    {titleCase(item)}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-light uppercase">Mandatory documents</p>
              <div className="flex flex-wrap gap-1.5">
                {(policy.mandatory_documents || []).map((item, index) => (
                  <span key={`${item}-${index}`} className="rounded-full border border-line bg-[#F4F2EE] px-2 py-0.5 text-[11px] text-ink/80">
                    {DOC_TYPE_LABEL[item] || titleCase(item)}
                  </span>
                ))}
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader
            title="Evidence"
            subtitle={`${documents.length} document(s)`}
            action={<Link to={`/documents?product=${product.product_id}`} className="text-xs text-brand-500 hover:text-brand-600">Vault</Link>}
          />
          {documents.length === 0 ? (
            <EmptyState icon="file" title="No evidence uploaded" description="Upload receipts, warranty cards or photos for faster adjudication." />
          ) : (
            <Table minWidth="min-w-[480px]">
              <THead>
                <tr>
                  <Th>Document</Th>
                  <Th>Type</Th>
                  <Th>Status</Th>
                  <Th />
                </tr>
              </THead>
              <TBody>
                {documents.map((doc) => (
                  <tr key={doc.doc_id}>
                    <Td>
                      <p className="max-w-[180px] truncate text-ink">{doc.file_name}</p>
                      <p className="text-[11px] text-muted-light">{formatDate(doc.created_at)}</p>
                    </Td>
                    <Td>{DOC_TYPE_LABEL[doc.file_type] || titleCase(doc.file_type)}</Td>
                    <Td>
                      <span className={doc.verified_at ? 'text-status-success' : 'text-status-warning'}>
                        {doc.verified_at ? 'Verified' : 'Pending'}
                      </span>
                    </Td>
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
          <CardHeader title="Repair history" subtitle={`${repairs.length} record(s)`} action={canIntake ? <Button size="sm" variant="ghost" icon="plus" onClick={() => setRepairOpen(true)}>Add</Button> : null} />
          {repairs.length === 0 ? (
            <EmptyState icon="wrench" title="No repairs logged" description="Authorized and unauthorized repairs influence the adjudication rules." />
          ) : (
            <Table minWidth="min-w-[520px]">
              <THead>
                <tr>
                  <Th>Date</Th>
                  <Th>Service center</Th>
                  <Th>Cost</Th>
                  <Th>Authorized</Th>
                </tr>
              </THead>
              <TBody>
                {repairs.map((repair) => (
                  <tr key={repair.repair_id}>
                    <Td>{formatDate(repair.repair_date)}</Td>
                    <Td>{repair.service_center_name}</Td>
                    <Td>{formatCurrency(repair.repair_cost)}</Td>
                    <Td>
                      <span className={repair.authorized ? 'text-status-success' : 'text-status-danger'}>
                        {repair.authorized ? 'Authorized' : 'Unauthorized'}
                      </span>
                    </Td>
                  </tr>
                ))}
              </TBody>
            </Table>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title="Claims on this product" subtitle={`${claims.length} claim(s)`} />
        {claims.length === 0 ? (
          <EmptyState icon="clipboard" title="No claims yet" description="Create a claim for this product to run the adjudication pipeline." action={<Link to={`/claims/new?product=${product.product_id}`} className={buttonClasses({ size: 'sm' })}>New claim</Link>} />
        ) : (
          <div className="flex flex-wrap gap-2 p-4">
            {claims.map((claimId) => (
              <Link key={claimId} to={`/claims/${claimId}`} className="rounded-lg border border-line bg-[#F4F2EE] px-3 py-1.5 text-xs text-brand-500 hover:border-brand-500/30 hover:text-brand-600">
                {claimId}
              </Link>
            ))}
          </div>
        )}
      </Card>

      <UploadEvidenceModal
        open={docOpen}
        onClose={() => setDocOpen(false)}
        productId={product.product_id}
        onDone={() => {
          setDocOpen(false)
          load()
        }}
      />
      <RepairModal
        open={repairOpen}
        onClose={() => setRepairOpen(false)}
        productId={product.product_id}
        onDone={() => {
          setRepairOpen(false)
          load()
        }}
      />
    </>
  )
}

function UploadEvidenceModal({ open, onClose, productId, onDone }) {
  const push = useToast((state) => state.push)
  const [fileType, setFileType] = useState('purchase_receipt')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    if (!file) {
      setError('Select a file to upload.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('upload', file)
      formData.append('file_type', fileType)
      formData.append('product_id', productId)
      const result = await uploadDocument(formData)
      push(result.warning || `Document ${result.doc_id} uploaded.`, result.warning ? 'info' : 'success')
      setFile(null)
      onDone()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Upload evidence"
      description="PDF, JPG or PNG up to 10 MB."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button form="upload-doc-form" type="submit" loading={busy}>Upload</Button>
        </>
      }
    >
      <form id="upload-doc-form" onSubmit={submit} className="space-y-4">
        <Select label="Document type" value={fileType} onChange={(event) => setFileType(event.target.value)}>
          {DOC_TYPES.map((type) => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </Select>
        <Input
          label="File"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
        {error && <p className="text-xs text-status-danger">{error}</p>}
      </form>
    </Modal>
  )
}

function RepairModal({ open, onClose, productId, onDone }) {
  const push = useToast((state) => state.push)
  const [form, setForm] = useState(EMPTY_REPAIR)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const update = (key) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await createRepair({
        product_id: productId,
        repair_date: form.repair_date,
        service_center_name: form.service_center_name,
        replaced_parts: form.replaced_parts,
        repair_cost: Number(form.repair_cost || 0),
        outcome: form.outcome,
        authorized: form.authorized,
      })
      push('Repair logged.')
      setForm(EMPTY_REPAIR)
      onDone()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Log a repair"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button form="repair-form" type="submit" loading={busy}>Save repair</Button>
        </>
      }
    >
      <form id="repair-form" onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Repair date" type="date" required value={form.repair_date} onChange={update('repair_date')} />
          <Input label="Service center" required value={form.service_center_name} onChange={update('service_center_name')} />
          <Input label="Cost (USD)" type="number" min="0" step="0.01" value={form.repair_cost} onChange={update('repair_cost')} />
          <Input label="Replaced parts" value={form.replaced_parts} onChange={update('replaced_parts')} />
        </div>
        <Textarea label="Outcome" value={form.outcome} onChange={update('outcome')} rows={2} />
        <Checkbox label="Authorized repair" checked={form.authorized} onChange={update('authorized')} />
        {error && <p className="text-xs text-status-danger">{error}</p>}
      </form>
    </Modal>
  )
}




