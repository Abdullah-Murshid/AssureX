import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import {
  deleteDocument,
  downloadDocument,
  listDocuments,
  replaceDocument,
  uploadDocument,
  verifyDocument,
} from '../api/documents'
import { listProducts } from '../api/products'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import { Input, Select } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import Modal from '../components/ui/Modal'
import Pagination from '../components/ui/Pagination'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { DOC_TYPES, DOC_TYPE_LABEL } from '../lib/constants'
import { formatDate, titleCase } from '../lib/format'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'

const VERIFY_FIELDS = [
  ['purchase_date', 'extracted_purchase_date', 'Purchase date'],
  ['invoice_number', 'extracted_invoice_number', 'Invoice number'],
  ['product_name', 'extracted_product_name', 'Product name'],
  ['model_number', 'extracted_model_number', 'Model number'],
  ['serial_number', 'extracted_serial_number', 'Serial number'],
  ['retailer_name', 'extracted_retailer', 'Retailer'],
  ['purchase_amount', 'extracted_amount', 'Amount'],
  ['warranty_period', 'extracted_warranty_period', 'Warranty period'],
]

export default function Documents() {
  const [searchParams] = useSearchParams()
  const push = useToast((state) => state.push)
  const user = useAuth((state) => state.user)
  const hasRole = useAuth((state) => state.hasRole)
  const canIntake = hasRole('customer', 'service_center')
  const canMutateDocument = (doc) =>
    user?.role === 'admin' || (canIntake && doc.user_id === user?.user_id)

  const [filters, setFilters] = useState({
    file_type: '',
    product_id: searchParams.get('product') || '',
  })
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [verifyDoc, setVerifyDoc] = useState(null)
  const [replaceDoc, setReplaceDoc] = useState(null)
  const [deleteDoc, setDeleteDoc] = useState(null)

  const query = useMemo(
    () => ({
      file_type: filters.file_type || undefined,
      product_id: filters.product_id || undefined,
      page,
      per_page: 10,
    }),
    [filters.file_type, filters.product_id, page],
  )

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    return listDocuments(query)
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [query])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    listProducts({ per_page: 100 })
      .then((result) => setProducts(result.items || []))
      .catch(() => setProducts([]))
  }, [])

  const productLabel = (productId) =>
    products.find((row) => row.product.product_id === productId)?.product.product_name || productId || '—'

  return (
    <>
      <PageHeader
        eyebrow="Evidence"
        title="Document vault"
        description="Receipts, warranty cards and photos with OCR extraction and duplicate detection."
        actions={
          canIntake ? (
            <Button icon="upload" onClick={() => setUploadOpen(true)}>
              Upload document
            </Button>
          ) : null
        }
      />

      <Card className="mb-5">
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Select
            label="Document type"
            value={filters.file_type}
            onChange={(event) => {
              setPage(1)
              setFilters((prev) => ({ ...prev, file_type: event.target.value }))
            }}
          >
            <option value="">All types</option>
            {DOC_TYPES.map((type) => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </Select>
          <Select
            label="Product"
            value={filters.product_id}
            onChange={(event) => {
              setPage(1)
              setFilters((prev) => ({ ...prev, product_id: event.target.value }))
            }}
          >
            <option value="">All products</option>
            {products.map((row) => (
              <option key={row.product.product_id} value={row.product.product_id}>
                {row.product.product_name}
              </option>
            ))}
          </Select>
          <div className="flex items-end">
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => {
                setPage(1)
                setFilters({ file_type: '', product_id: '' })
              }}
            >
              Clear filters
            </Button>
          </div>
        </div>
      </Card>

      {error && (
        <p className="mb-4 rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">
          {error}
        </p>
      )}

      <Card>
        <CardHeader title="Uploaded evidence" subtitle={`${data?.total ?? 0} document(s)`} />
        {loading && !data ? (
          <Spinner label="Loading documents…" />
        ) : data?.items?.length ? (
          <>
            <Table minWidth="min-w-[900px]">
              <THead>
                <tr>
                  <Th>Document</Th>
                  <Th>Type</Th>
                  <Th>Linked to</Th>
                  <Th>Status</Th>
                  <Th>Uploaded</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </THead>
              <TBody>
                {data.items.map((doc) => (
                  <tr key={doc.doc_id} className="transition-colors hover:bg-[#FAFAF8]">
                    <Td>
                      <p className="max-w-[220px] truncate text-ink">{doc.file_name}</p>
                      <p className="text-[11px] text-muted-light">
                        {doc.doc_id} · <span className="tabular-nums">{doc.file_hash?.slice(0, 10)}…</span>
                      </p>
                      {doc.duplicate_of?.length > 0 && (
                        <p className="mt-1 text-[11px] text-status-warning">
                          Duplicate of {doc.duplicate_of.join(', ')}
                        </p>
                      )}
                    </Td>
                    <Td>{DOC_TYPE_LABEL[doc.file_type] || titleCase(doc.file_type)}</Td>
                    <Td>
                      <p className="text-ink/80">{doc.claim_id || doc.product_id ? productLabel(doc.product_id) : 'Unlinked'}</p>
                      {doc.claim_id && <p className="text-[11px] text-brand-500">{doc.claim_id}</p>}
                    </Td>
                    <Td>
                      <span className={doc.verified_at ? 'text-status-success' : 'text-status-warning'}>
                        {doc.verified_at ? 'Verified' : 'Pending review'}
                      </span>
                    </Td>
                    <Td className="whitespace-nowrap">{formatDate(doc.created_at)}</Td>
                    <Td>
                      <div className="flex justify-end gap-1">
                        <IconButton
                          icon="download"
                          label="Download"
                          onClick={() => downloadDocument(doc.doc_id, doc.file_name).catch((err) => push(errorMessage(err), 'error'))}
                        />
                        {canMutateDocument(doc) && (
                          <>
                            <IconButton icon="check" label="Verify OCR fields" onClick={() => setVerifyDoc(doc)} />
                            <IconButton icon="refresh" label="Replace file" onClick={() => setReplaceDoc(doc)} />
                            <IconButton icon="trash" label="Delete" danger onClick={() => setDeleteDoc(doc)} />
                          </>
                        )}
                      </div>
                    </Td>
                  </tr>
                ))}
              </TBody>
            </Table>
            <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onPage={setPage} />
          </>
        ) : (
          <EmptyState
            icon="file"
            title="No documents"
            description="Upload a receipt, warranty card or product photo to attach it to a claim."
            action={
              canIntake ? (
                <Button size="sm" icon="upload" onClick={() => setUploadOpen(true)}>Upload document</Button>
              ) : null
            }
          />
        )}
      </Card>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} products={products} onDone={() => { setUploadOpen(false); load() }} />
      <VerifyModal key={`verify-${verifyDoc?.doc_id || 'none'}`} doc={verifyDoc} onClose={() => setVerifyDoc(null)} onDone={() => { setVerifyDoc(null); load() }} />
      <ReplaceModal key={`replace-${replaceDoc?.doc_id || 'none'}`} doc={replaceDoc} onClose={() => setReplaceDoc(null)} onDone={() => { setReplaceDoc(null); load() }} />
      <DeleteModal doc={deleteDoc} onClose={() => setDeleteDoc(null)} onDone={() => { setDeleteDoc(null); load() }} />
    </>
  )
}

function IconButton({ icon, label, onClick, danger = false }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className={`rounded-lg p-1.5 transition-colors ${
        danger
          ? 'text-muted-light hover:bg-status-danger/10 hover:text-status-danger'
          : 'text-muted-light hover:bg-[#F4F2EE] hover:text-ink'
      }`}
    >
      <Icon name={icon} size={15} />
    </button>
  )
}

function UploadModal({ open, onClose, products, onDone }) {
  const push = useToast((state) => state.push)
  const [fileType, setFileType] = useState('purchase_receipt')
  const [productId, setProductId] = useState('')
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
      if (productId) formData.append('product_id', productId)
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
      title="Upload document"
      description="PDF, JPG or PNG up to 10 MB. Receipts are parsed with OCR."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button form="doc-upload-form" type="submit" loading={busy}>Upload</Button>
        </>
      }
    >
      <form id="doc-upload-form" onSubmit={submit} className="space-y-4">
        <Select label="Document type" value={fileType} onChange={(event) => setFileType(event.target.value)}>
          {DOC_TYPES.map((type) => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </Select>
        <Select label="Link to product (optional)" value={productId} onChange={(event) => setProductId(event.target.value)}>
          <option value="">No product</option>
          {products.map((row) => (
            <option key={row.product.product_id} value={row.product.product_id}>
              {row.product.product_name} · <span className="font-mono">{row.product.serial_number}</span>
            </option>
          ))}
        </Select>
        <Input label="File" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        {error && <p className="text-xs text-status-danger">{error}</p>}
      </form>
    </Modal>
  )
}

function VerifyModal({ doc, onClose, onDone }) {
  const push = useToast((state) => state.push)
  const [form, setForm] = useState(() => {
    const extracted = doc?.extracted_data || {}
    return Object.fromEntries(
      VERIFY_FIELDS.map(([key, source]) => [key, extracted[source] ?? '']),
    )
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await verifyDocument(doc.doc_id, form)
      push('Extracted fields saved.')
      onDone()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={Boolean(doc)}
      onClose={onClose}
      title="Verify OCR fields"
      description={doc ? `${doc.file_name} · ${doc.doc_id}` : ''}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button form="verify-form" type="submit" loading={busy}>Save fields</Button>
        </>
      }
    >
      <form id="verify-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        {VERIFY_FIELDS.map(([key, , label]) => (
          <Input
            key={key}
            label={label}
            value={form[key] ?? ''}
            onChange={(event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))}
          />
        ))}
        {error && <p className="text-xs text-status-danger sm:col-span-2">{error}</p>}
      </form>
    </Modal>
  )
}

function ReplaceModal({ doc, onClose, onDone }) {
  const push = useToast((state) => state.push)
  const [file, setFile] = useState(null)
  const [fileType, setFileType] = useState(doc?.file_type || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    if (!file) {
      setError('Select a replacement file.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('upload', file)
      if (fileType) formData.append('file_type', fileType)
      const result = await replaceDocument(doc.doc_id, formData)
      push(`Document ${result.doc_id} replaced.`)
      onDone()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={Boolean(doc)}
      onClose={onClose}
      title="Replace document"
      description={doc ? `Replacing ${doc.file_name}` : ''}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button form="replace-form" type="submit" loading={busy}>Replace</Button>
        </>
      }
    >
      <form id="replace-form" onSubmit={submit} className="space-y-4">
        <Select label="Document type" value={fileType} onChange={(event) => setFileType(event.target.value)}>
          {DOC_TYPES.map((type) => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </Select>
        <Input label="New file" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        {error && <p className="text-xs text-status-danger">{error}</p>}
      </form>
    </Modal>
  )
}

function DeleteModal({ doc, onClose, onDone }) {
  const push = useToast((state) => state.push)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      await deleteDocument(doc.doc_id)
      push(`Document ${doc.doc_id} deleted.`)
      onDone()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={Boolean(doc)}
      onClose={onClose}
      title="Delete document"
      description="This removes the database record and the stored file."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="danger" loading={busy} onClick={submit}>Delete</Button>
        </>
      }
    >
      <p className="text-sm text-ink/80">
        Delete <strong className="text-ink">{doc?.file_name}</strong> ({doc?.doc_id})?
      </p>
      {doc?.claim_id && (
        <p className="mt-2 text-xs text-status-warning">
          This document is referenced by claim {doc.claim_id}; removing it may leave the claim without evidence.
        </p>
      )}
      {error && <p className="mt-2 text-xs text-status-danger">{error}</p>}
    </Modal>
  )
}


