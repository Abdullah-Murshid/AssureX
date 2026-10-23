import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { createProduct } from '../api/products'
import Button, { buttonClasses } from '../components/ui/Button'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import { PageHeader } from '../components/ui/Feedback'
import { Checkbox, Input, Select } from '../components/ui/Fields'
import { CATEGORIES } from '../lib/constants'
import { useToast } from '../store/toast'

const INITIAL = {
  product_name: '',
  category: 'electronics',
  brand: '',
  model_number: '',
  serial_number: '',
  purchase_date: '',
  purchase_price: '',
  retailer: '',
  warranty_duration_months: 24,
  has_extended_warranty: false,
  extended_warranty_provider: '',
  extended_warranty_contract_number: '',
  extended_warranty_duration_months: 0,
}

export default function ProductNew() {
  const [form, setForm] = useState(INITIAL)
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const push = useToast((state) => state.push)

  const update = (key) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const validate = () => {
    const next = {}
    if (!form.product_name.trim()) next.product_name = 'Product name is required.'
    if (!form.serial_number.trim()) next.serial_number = 'Serial number is required.'
    if (!form.purchase_date) next.purchase_date = 'Purchase date is required.'
    if (form.purchase_price === '' || Number(form.purchase_price) < 0) {
      next.purchase_price = 'Enter a valid price.'
    }
    if (Number(form.warranty_duration_months) < 1) {
      next.warranty_duration_months = 'Warranty must be at least 1 month.'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')
    if (!validate()) return
    setLoading(true)
    try {
      const payload = {
        ...form,
        purchase_price: Number(form.purchase_price),
        warranty_duration_months: Number(form.warranty_duration_months),
        extended_warranty_duration_months: Number(form.extended_warranty_duration_months),
      }
      const result = await createProduct(payload)
      push(`Product ${result.product.product_id} registered.`)
      navigate(`/products/${result.product.product_id}`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Coverage"
        title="Register a product"
        description="Coverage windows and policy rules are derived from the purchase date and category."
        actions={
          <Link to="/products" className={buttonClasses({ variant: 'secondary' })}>
            Back to products
          </Link>
        }
      />

      <form onSubmit={onSubmit} className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader title="Product details" subtitle="Identify the covered device" />
            <CardBody className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Product name"
                required
                value={form.product_name}
                onChange={update('product_name')}
                error={errors.product_name}
                placeholder="ULTRAVIEW 4K TV"
              />
              <Select label="Category" value={form.category} onChange={update('category')}>
                {CATEGORIES.map((category) => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </Select>
              <Input label="Brand" value={form.brand} onChange={update('brand')} placeholder="APEX" />
              <Input
                label="Model number"
                value={form.model_number}
                onChange={update('model_number')}
                placeholder="AV-4K-55"
              />
              <Input
                label="Serial number"
                required
                value={form.serial_number}
                onChange={update('serial_number')}
                error={errors.serial_number}
                placeholder="SN-TX-1001"
              />
              <Input
                label="Retailer"
                value={form.retailer}
                onChange={update('retailer')}
                placeholder="Authorized retailer"
              />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Purchase & warranty" subtitle="Used to compute remaining coverage" />
            <CardBody className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Purchase date"
                type="date"
                required
                value={form.purchase_date}
                onChange={update('purchase_date')}
                error={errors.purchase_date}
              />
              <Input
                label="Purchase price (USD)"
                type="number"
                min="0"
                step="0.01"
                required
                value={form.purchase_price}
                onChange={update('purchase_price')}
                error={errors.purchase_price}
                placeholder="970.00"
              />
              <Input
                label="Warranty duration (months)"
                type="number"
                min="1"
                required
                value={form.warranty_duration_months}
                onChange={update('warranty_duration_months')}
                error={errors.warranty_duration_months}
              />
              <div className="flex items-end pb-2">
                <Checkbox
                  label="Extended warranty"
                  checked={form.has_extended_warranty}
                  onChange={update('has_extended_warranty')}
                />
              </div>
            </CardBody>
          </Card>

          {form.has_extended_warranty && (
            <Card>
              <CardHeader title="Extended warranty" subtitle="Optional protection plan" />
              <CardBody className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Provider"
                  value={form.extended_warranty_provider}
                  onChange={update('extended_warranty_provider')}
                  placeholder="SafeGuard Plus"
                />
                <Input
                  label="Contract number"
                  value={form.extended_warranty_contract_number}
                  onChange={update('extended_warranty_contract_number')}
                  placeholder="EW-2026-001"
                />
                <Input
                  label="Extra coverage (months)"
                  type="number"
                  min="0"
                  value={form.extended_warranty_duration_months}
                  onChange={update('extended_warranty_duration_months')}
                />
              </CardBody>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card>
            <CardBody className="space-y-3 text-xs text-muted">
              <p className="text-sm font-medium text-ink">Before you register</p>
              <p>Coverage starts on the purchase date and follows the category policy duration.</p>
              <p>Claims require the mandatory documents defined by the category policy.</p>
              <p>Evidence can be uploaded from the Documents vault after registration.</p>
            </CardBody>
          </Card>

          {error && (
            <p className="rounded-xl border border-status-danger/30 bg-status-danger/10 px-3 py-2 text-xs text-status-danger">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full">
            Register product
          </Button>
        </div>
      </form>
    </>
  )
}


