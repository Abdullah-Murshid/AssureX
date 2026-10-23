import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { precheckClaim, submitClaim } from '../api/claims'
import { listDocuments } from '../api/documents'
import { listProducts } from '../api/products'
import { FILE_TYPE_FIELDS } from '../lib/claimFiles'
import Badge from '../components/ui/Badge'
import Button, { buttonClasses } from '../components/ui/Button'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import { PageHeader, Spinner } from '../components/ui/Feedback'
import { Checkbox, Input, Select, Textarea } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import { CATEGORIES, DAMAGE_TYPES, FAULT_CATEGORIES } from '../lib/constants'
import { formatDate, titleCase } from '../lib/format'
import { useToast } from '../store/toast'

const STEPS = ['Product', 'Incident', 'Evidence', 'Review']
const TODAY = new Date().toISOString().slice(0, 10)

const emptyNewProduct = {
  product_name: '',
  product_category: 'electronics',
  brand: '',
  model_number: '',
  serial_number: '',
  purchase_date: '',
  purchase_price: '',
  retailer: '',
  warranty_months: 24,
}

export default function ClaimNew() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const push = useToast((state) => state.push)

  const [step, setStep] = useState(0)
  const [products, setProducts] = useState([])
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [mode, setMode] = useState('existing')
  const [productId, setProductId] = useState(searchParams.get('product') || '')
  const [newProduct, setNewProduct] = useState(emptyNewProduct)
  const [incident, setIncident] = useState({
    fault_category: 'motherboard_failure',
    damage_type: 'none',
    fault_occurrence_date: '',
    claim_submission_date: TODAY,
    description: '',
  })
  const [files, setFiles] = useState({})
  const [vaultDocs, setVaultDocs] = useState([])
  const [attached, setAttached] = useState([])
  const [precheck, setPrecheck] = useState(null)
  const [checking, setChecking] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const selectedProduct = useMemo(
    () => products.find((row) => row.product.product_id === productId)?.product || null,
    [products, productId],
  )

  useEffect(() => {
    listProducts({ per_page: 100 })
      .then((result) => {
        const items = result.items || []
        setProducts(items)
        if (!productId && items.length) {
          setProductId(items[0].product.product_id)
        }
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoadingProducts(false))
  }, [productId])

  useEffect(() => {
    if (!productId) return
    listDocuments({ product_id: productId, per_page: 100 })
      .then((result) => setVaultDocs(result.items || []))
      .catch(() => setVaultDocs([]))
  }, [productId])

  const faultOptions = useMemo(() => {
    const covered = selectedProduct?.category
      ? products.find((row) => row.product.product_id === productId)?.policy?.covered_faults || []
      : []
    const merged = [...new Set([...covered, ...FAULT_CATEGORIES.map((item) => item.value)])]
    return merged.map((value) => ({
      value,
      label: FAULT_CATEGORIES.find((item) => item.value === value)?.label || titleCase(value),
    }))
  }, [products, productId, selectedProduct])

  const runPrecheck = async () => {
    if (mode === 'new') {
      // Pre-check needs a persisted product; inline registrations run at submit.
      setPrecheck(null)
      return null
    }
    if (!productId) return null
    if (!incident.fault_occurrence_date) return null
    setChecking(true)
    try {
      const result = await precheckClaim({
        product_id: productId,
        fault_occurrence_date: incident.fault_occurrence_date,
        claim_submission_date: incident.claim_submission_date,
        fault_category: incident.fault_category,
        damage_type: incident.damage_type,
      })
      setPrecheck(result)
      return result
    } catch (err) {
      setPrecheck({ ready: false, warnings: [errorMessage(err)], missing_documents: [], contradictions: [], recommended_actions: [] })
      return null
    } finally {
      setChecking(false)
    }
  }

  const canContinue = () => {
    if (step === 0) return mode === 'existing' ? Boolean(productId) : Boolean(newProduct.product_name && newProduct.serial_number && newProduct.purchase_date)
    if (step === 1) return Boolean(incident.fault_occurrence_date && incident.fault_category)
    return true
  }

  const next = async () => {
    setError('')
    if (!canContinue()) {
      setError('Complete the required fields before continuing.')
      return
    }
    if (step === 1) {
      await runPrecheck()
    }
    setStep((value) => Math.min(value + 1, STEPS.length - 1))
  }

  const buildFormData = (actionType) => {
    const formData = new FormData()
    const fields = {
      product_id: mode === 'existing' ? productId : '',
      product_name: newProduct.product_name,
      product_category: newProduct.product_category,
      brand: newProduct.brand,
      model_number: newProduct.model_number,
      serial_number: newProduct.serial_number,
      purchase_date: newProduct.purchase_date,
      purchase_price: newProduct.purchase_price || 0,
      retailer: newProduct.retailer,
      warranty_months: newProduct.warranty_months || 24,
      fault_category: incident.fault_category,
      damage_type: incident.damage_type,
      fault_occurrence_date: incident.fault_occurrence_date,
      claim_submission_date: incident.claim_submission_date,
      description: incident.description,
      attach_doc_ids: attached.join(','),
      action_type: actionType,
    }
    Object.entries(fields).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') formData.append(key, value)
    })
    FILE_TYPE_FIELDS.forEach(([field]) => {
      if (files[field]) formData.append(field, files[field])
    })
    return formData
  }

  const submit = async (actionType) => {
    setError('')
    setSubmitting(true)
    try {
      const result = await submitClaim(buildFormData(actionType))
      push(actionType === 'draft' ? 'Draft saved.' : `Claim ${result.claim_id} submitted.`)
      navigate(`/claims/${result.claim_id}`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (loadingProducts) return <Spinner label="Loading products…" />

  return (
    <>
      <PageHeader
        eyebrow="Adjudication"
        title="Submit a warranty claim"
        description="Product, incident and evidence — validated against policy before the AI models run."
        actions={
          <Link to="/claims" className={buttonClasses({ variant: 'secondary' })}>
            Cancel
          </Link>
        }
      />

      <ol className="mb-6 flex flex-wrap items-center gap-2 text-xs">
        {STEPS.map((label, index) => (
          <li key={label} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => index < step && setStep(index)}
              className={`flex items-center gap-2 rounded-full border px-3 py-1.5 transition-colors ${
                index === step
                  ? 'border-brand-500/30 bg-tint text-brand-500'
                  : index < step
                    ? 'border-status-success/30 bg-status-success/10 text-status-success'
                    : 'border-line text-muted-light'
              }`}
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#FAFAF8] text-[10px]">
                {index < step ? '✓' : index + 1}
              </span>
              {label}
            </button>
            {index < STEPS.length - 1 && <Icon name="chevronRight" size={14} className="text-muted-light" />}
          </li>
        ))}
      </ol>

      {error && (
        <p className="mb-4 rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">
          {error}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {step === 0 && (
            <ProductStep
              mode={mode}
              setMode={setMode}
              products={products}
              productId={productId}
              setProductId={setProductId}
              newProduct={newProduct}
              setNewProduct={setNewProduct}
            />
          )}

          {step === 1 && (
            <Card>
              <CardHeader title="Incident details" subtitle="What happened, and when" />
              <CardBody className="grid gap-4 sm:grid-cols-2">
                <Select
                  label="Fault category"
                  value={incident.fault_category}
                  onChange={(event) => setIncident((prev) => ({ ...prev, fault_category: event.target.value }))}
                >
                  {faultOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </Select>
                <Select
                  label="Damage type"
                  value={incident.damage_type}
                  onChange={(event) => setIncident((prev) => ({ ...prev, damage_type: event.target.value }))}
                >
                  {DAMAGE_TYPES.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </Select>
                <Input
                  label="Fault occurrence date"
                  type="date"
                  required
                  value={incident.fault_occurrence_date}
                  onChange={(event) => setIncident((prev) => ({ ...prev, fault_occurrence_date: event.target.value }))}
                />
                <Input
                  label="Claim submission date"
                  type="date"
                  value={incident.claim_submission_date}
                  onChange={(event) => setIncident((prev) => ({ ...prev, claim_submission_date: event.target.value }))}
                />
                <Textarea
                  label="Description"
                  className="sm:col-span-2"
                  rows={4}
                  value={incident.description}
                  onChange={(event) => setIncident((prev) => ({ ...prev, description: event.target.value }))}
                  placeholder="Describe the fault and how it occurred…"
                />
              </CardBody>
            </Card>
          )}

          {step === 2 && (
            <EvidenceStep
              files={files}
              setFiles={setFiles}
              vaultDocs={vaultDocs}
              attached={attached}
              setAttached={setAttached}
              precheck={precheck}
            />
          )}

          {step === 3 && (
            <ReviewStep
              product={selectedProduct}
              newProduct={newProduct}
              mode={mode}
              incident={incident}
              files={files}
              attached={attached}
              precheck={precheck}
              checking={checking}
            />
          )}

          <div className="mt-4 flex items-center justify-between">
            <Button
              variant="ghost"
              onClick={() => setStep((value) => Math.max(0, value - 1))}
              disabled={step === 0}
            >
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button onClick={next} loading={checking}>
                Continue
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => submit('draft')} loading={submitting}>
                  Save draft
                </Button>
                <Button icon="spark" onClick={() => submit('submit')} loading={submitting}>
                  Submit for adjudication
                </Button>
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader title="Pre-check" subtitle="Policy readiness signal" />
            <CardBody>
              {!precheck ? (
                <p className="text-xs text-muted-light">
                  Complete the incident step to run the policy pre-check.
                </p>
              ) : (
                <div className="space-y-3 text-xs">
                  <Badge tone={precheck.ready ? 'success' : 'warning'} dot>
                    {precheck.ready ? 'Ready to submit' : 'Needs attention'}
                  </Badge>
                  {precheck.missing_documents?.length > 0 && (
                    <div>
                      <p className="text-muted">Missing documents</p>
                      <p className="text-status-warning">{precheck.missing_documents.join(', ')}</p>
                    </div>
                  )}
                  {precheck.contradictions?.length > 0 && (
                    <div>
                      <p className="text-muted">Contradictions</p>
                      <ul className="list-disc space-y-1 pl-4 text-status-danger">
                        {precheck.contradictions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                      </ul>
                    </div>
                  )}
                  {precheck.warnings?.length > 0 && (
                    <div>
                      <p className="text-muted">Warnings</p>
                      <ul className="list-disc space-y-1 pl-4 text-status-warning">
                        {precheck.warnings.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                      </ul>
                    </div>
                  )}
                  <p className="border-t border-line/70 pt-2 text-muted-light">
                    Remaining warranty: <span className="text-ink/80">{precheck.remaining_warranty_days ?? '—'} days</span>
                  </p>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardBody className="text-xs text-muted-light">
              <p className="mb-2 font-medium text-ink/80">Adjudication pipeline</p>
              <ol className="space-y-1.5">
                <li>1. Derived features (warranty, serial, repairs)</li>
                <li>2. Policy rule + contradiction checks</li>
                <li>3. XGBoost tabular prediction</li>
                <li>4. Summary card rendered → GTM vision prediction</li>
                <li>5. Fusion → final decision</li>
              </ol>
            </CardBody>
          </Card>
        </aside>
      </div>
    </>
  )
}

function ProductStep({ mode, setMode, products, productId, setProductId, newProduct, setNewProduct }) {
  const update = (key) => (event) => setNewProduct((prev) => ({ ...prev, [key]: event.target.value }))
  return (
    <Card>
      <CardHeader title="Product" subtitle="Choose a registered product or register one inline" />
      <CardBody className="space-y-4">
        <div className="flex gap-2">
          <Button variant={mode === 'existing' ? 'primary' : 'secondary'} size="sm" onClick={() => setMode('existing')}>
            Registered product
          </Button>
          <Button variant={mode === 'new' ? 'primary' : 'secondary'} size="sm" onClick={() => setMode('new')}>
            New product
          </Button>
        </div>

        {mode === 'existing' ? (
          products.length === 0 ? (
            <p className="text-xs text-muted">
              No products yet. Switch to "New product" or{' '}
              <Link to="/products/new" className="text-brand-500 hover:text-brand-600">register one</Link>.
            </p>
          ) : (
            <div className="grid max-h-[420px] gap-2 overflow-y-auto pr-1">
              {products.map((row) => (
                <button
                  key={row.product.product_id}
                  type="button"
                  onClick={() => setProductId(row.product.product_id)}
                  className={`flex items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
                    productId === row.product.product_id
                      ? 'border-brand-500/50 bg-tint'
                      : 'border-line bg-[#FAFAF8] hover:border-line-input'
                  }`}
                >
                  <div>
                    <p className="text-sm text-ink">{row.product.product_name}</p>
                    <p className="text-[11px] text-muted-light">
                      {row.product.brand} · <span className="font-mono">{row.product.serial_number}</span> · expires {formatDate(row.warranty_expiry_date)}
                    </p>
                  </div>
                  <Badge tone={row.warranty_status === 'Active' ? 'success' : 'warning'}>
                    {row.warranty_status}
                  </Badge>
                </button>
              ))}
            </div>
          )
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Product name" required value={newProduct.product_name} onChange={update('product_name')} />
            <Select label="Category" value={newProduct.product_category} onChange={update('product_category')}>
              {CATEGORIES.map((category) => (
                <option key={category.value} value={category.value}>{category.label}</option>
              ))}
            </Select>
            <Input label="Brand" value={newProduct.brand} onChange={update('brand')} />
            <Input label="Model number" value={newProduct.model_number} onChange={update('model_number')} />
            <Input label="Serial number" required value={newProduct.serial_number} onChange={update('serial_number')} />
            <Input label="Purchase date" type="date" required value={newProduct.purchase_date} onChange={update('purchase_date')} />
            <Input label="Purchase price (USD)" type="number" min="0" value={newProduct.purchase_price} onChange={update('purchase_price')} />
            <Input label="Retailer" value={newProduct.retailer} onChange={update('retailer')} />
            <Input label="Warranty months" type="number" min="1" value={newProduct.warranty_months} onChange={update('warranty_months')} />
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function EvidenceStep({ files, setFiles, vaultDocs, attached, setAttached, precheck }) {
  const toggleAttached = (docId) =>
    setAttached((prev) => (prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]))

  return (
    <Card>
      <CardHeader
        title="Evidence"
        subtitle="Upload new files or attach documents already in the vault"
        action={precheck && <Badge tone={precheck.ready ? 'success' : 'warning'}>{precheck.ready ? 'Policy ready' : 'Incomplete'}</Badge>}
      />
      <CardBody className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          {FILE_TYPE_FIELDS.map(([field, label, accept]) => (
            <div key={field} className="rounded-xl border border-line bg-[#FAFAF8] p-3">
              <p className="mb-2 text-xs font-medium text-ink/80">{label}</p>
              <input
                type="file"
                accept={accept}
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  setFiles((prev) => {
                    const next = { ...prev }
                    if (file) next[field] = file
                    else delete next[field]
                    return next
                  })
                }}
                className="w-full text-xs text-muted file:mr-2 file:rounded-lg file:border-0 file:bg-tint file:px-2.5 file:py-1.5 file:text-xs file:text-brand-500"
              />
              {files[field] && <p className="mt-1 truncate text-[11px] text-status-success">{files[field].name}</p>}
            </div>
          ))}
        </div>

        <div>
          <p className="mb-2 text-xs font-medium text-ink/80">Attach from vault</p>
          {vaultDocs.length === 0 ? (
            <p className="text-xs text-muted-light">No vault documents linked to this product.</p>
          ) : (
            <div className="max-h-56 space-y-1.5 overflow-y-auto pr-1">
              {vaultDocs.map((doc) => (
                <Checkbox
                  key={doc.doc_id}
                  label={`${doc.file_name} · ${doc.file_type}`}
                  checked={attached.includes(doc.doc_id)}
                  onChange={() => toggleAttached(doc.doc_id)}
                />
              ))}
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

function ReviewStep({ product, newProduct, mode, incident, files, attached, precheck, checking }) {
  const productLabel = mode === 'existing' ? product?.product_name : newProduct.product_name
  const rows = [
    ['Product', productLabel || '—'],
    ['Serial', mode === 'existing' ? product?.serial_number : newProduct.serial_number],
    ['Fault', titleCase(incident.fault_category)],
    ['Damage', titleCase(incident.damage_type)],
    ['Occurred', formatDate(incident.fault_occurrence_date)],
    ['Submitted', formatDate(incident.claim_submission_date)],
    ['Uploads', Object.keys(files).length],
    ['Attached docs', attached.length],
  ]
  return (
    <Card>
      <CardHeader title="Review & submit" subtitle="Confirm the claim before running both models" />
      <CardBody className="space-y-4">
        <dl className="grid gap-3 sm:grid-cols-2">
          {rows.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-line/70 bg-[#FAFAF8] px-3 py-2">
              <dt className="text-[11px] text-muted-light">{label}</dt>
              <dd className="text-sm text-ink">{value ?? '—'}</dd>
            </div>
          ))}
        </dl>

        {incident.description && (
          <div>
            <p className="text-[11px] text-muted-light">Description</p>
            <p className="mt-1 text-sm text-ink/80">{incident.description}</p>
          </div>
        )}

        {checking && <p className="text-xs text-muted">Running policy pre-check…</p>}
        {precheck && !precheck.ready && (
          <p className="rounded-lg border border-status-warning/30 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">
            Pre-check flagged issues — the claim will still be evaluated, but may require manual review.
          </p>
        )}
      </CardBody>
    </Card>
  )
}



