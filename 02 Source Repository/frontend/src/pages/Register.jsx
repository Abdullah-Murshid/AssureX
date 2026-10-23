import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import AuthLayout from '../components/layout/AuthLayout'
import Button from '../components/ui/Button'
import { Input, Select } from '../components/ui/Fields'
import { useAuth } from '../store/auth'

export default function Register() {
  const register = useAuth((state) => state.register)
  const navigate = useNavigate()

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    confirm: '',
    role: 'customer',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const update = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
      })
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Customers and service-center agents can register themselves."
      footer={
        <>
          Already registered?{' '}
          <Link to="/login" className="font-medium text-brand-500 hover:text-brand-600">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Input
          label="Full name"
          required
          value={form.full_name}
          onChange={update('full_name')}
          placeholder="Ayesha Khan"
          autoComplete="name"
        />
        <Input
          label="Email"
          type="email"
          required
          value={form.email}
          onChange={update('email')}
          placeholder="you@company.com"
          autoComplete="email"
        />
        <Select label="Account type" value={form.role} onChange={update('role')}>
          <option value="customer">Customer</option>
          <option value="service_center">Service Center</option>
        </Select>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Password"
            type="password"
            required
            value={form.password}
            onChange={update('password')}
            autoComplete="new-password"
            placeholder="At least 8 characters"
          />
          <Input
            label="Confirm password"
            type="password"
            required
            value={form.confirm}
            onChange={update('confirm')}
            autoComplete="new-password"
            placeholder="Repeat password"
          />
        </div>

        {error && (
          <p role="alert" className="rounded-lg border border-status-danger/20 bg-status-danger/[0.05] px-3 py-2 text-[12px] text-status-danger">
            {error}
          </p>
        )}

        <Button type="submit" loading={loading} className="w-full">
          Create account
        </Button>
      </form>
    </AuthLayout>
  )
}


