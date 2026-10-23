import { useEffect, useState } from 'react'

import { errorMessage } from '../api/client'
import { listProducts } from '../api/products'
import { createRepair, listRepairs } from '../api/repairs'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import { EmptyState, PageHeader, Spinner } from '../components/ui/Feedback'
import { Checkbox, Input, Select, Textarea } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import Modal from '../components/ui/Modal'
import Pagination from '../components/ui/Pagination'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { formatCurrency, formatDate } from '../lib/format'
import { useToast } from '../store/toast'

const EMPTY = {
  product_id: '',
  repair_date: '',
  service_center_name: '',
  replaced_parts: '',
  repair_cost: '',
  outcome: '',
  authorized: true,
}

export default function Repairs() {
  const push = useToast((state) => state.push)
  const [data, setData] = useState(null)
  const [products, setProducts] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    listRepairs({ page, per_page: 12 })
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  useEffect(() => {
    listProducts({ per_page: 100 })
      .then((result) => setProducts(result.items || []))
      .catch(() => setProducts([]))
  }, [])

  const update = (key) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setFormError('')
    if (!form.product_id || !form.repair_date || !form.service_center_name) {
      setFormError('Product, repair date and service center are required.')
      return
    }
    setBusy(true)
    try {
      await createRepair({
        ...form,
        repair_cost: Number(form.repair_cost || 0),
      })
      push('Repair logged.')
      setForm(EMPTY)
      setOpen(false)
      load()
    } catch (err) {
      setFormError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const productLabel = (productId) =>
    products.find((row) => row.product.product_id === productId)?.product.product_name || productId

  return (
    <>
      <PageHeader
        eyebrow="History"
        title="Repair records"
        description="Service history influences repair-frequency and authorization rules."
        actions={
          <Button icon="plus" onClick={() => setOpen(true)}>
            Log repair
          </Button>
        }
      />

      {error && (
        <p className="mb-4 rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">
          {error}
        </p>
      )}

      <Card>
        <CardHeader title="All repairs" subtitle={`${data?.total ?? 0} record(s)`} />
        {loading && !data ? (
          <Spinner label="Loading repairs…" />
        ) : data?.items?.length ? (
          <>
            <Table minWidth="min-w-[760px]">
              <THead>
                <tr>
                  <Th>Repair</Th>
                  <Th>Product</Th>
                  <Th>Date</Th>
                  <Th>Service center</Th>
                  <Th>Cost</Th>
                  <Th>Authorization</Th>
                </tr>
              </THead>
              <TBody>
                {data.items.map((repair) => (
                  <tr key={repair.repair_id}>
                    <Td className="text-ink">{repair.repair_id}</Td>
                    <Td>{productLabel(repair.product_id)}</Td>
                    <Td>{formatDate(repair.repair_date)}</Td>
                    <Td>
                      <p className="text-ink/80">{repair.service_center_name}</p>
                      <p className="text-[11px] text-muted-light">{repair.replaced_parts}</p>
                    </Td>
                    <Td>{formatCurrency(repair.repair_cost)}</Td>
                    <Td>
                      <Badge tone={repair.authorized ? 'success' : 'danger'} dot>
                        {repair.authorized ? 'Authorized' : 'Unauthorized'}
                      </Badge>
                    </Td>
                  </tr>
                ))}
              </TBody>
            </Table>
            <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onPage={setPage} />
          </>
        ) : (
          <EmptyState
            icon="wrench"
            title="No repairs recorded"
            description="Log a repair to keep the product's service history accurate."
            action={<Button size="sm" icon="plus" onClick={() => setOpen(true)}>Log repair</Button>}
          />
        )}
      </Card>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Log a repair"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button form="repair-page-form" type="submit" loading={busy}>Save</Button>
          </>
        }
      >
        <form id="repair-page-form" onSubmit={submit} className="space-y-4">
          <Select label="Product" required value={form.product_id} onChange={update('product_id')}>
            <option value="">Select product</option>
            {products.map((row) => (
              <option key={row.product.product_id} value={row.product.product_id}>
                {row.product.product_name} · <span className="font-mono">{row.product.serial_number}</span>
              </option>
            ))}
          </Select>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Repair date" type="date" required value={form.repair_date} onChange={update('repair_date')} />
            <Input label="Service center" required value={form.service_center_name} onChange={update('service_center_name')} />
            <Input label="Cost (USD)" type="number" min="0" step="0.01" value={form.repair_cost} onChange={update('repair_cost')} />
            <Input label="Replaced parts" value={form.replaced_parts} onChange={update('replaced_parts')} />
          </div>
          <Textarea label="Outcome" rows={2} value={form.outcome} onChange={update('outcome')} />
          <Checkbox label="Authorized repair" checked={form.authorized} onChange={update('authorized')} />
          {formError && <p className="text-xs text-status-danger">{formError}</p>}
        </form>
      </Modal>

      <p className="mt-4 flex items-center gap-2 text-[11px] text-muted-light">
        <Icon name="alert" size={13} /> Unauthorized repairs trigger a manual-review rule.
      </p>
    </>
  )
}


