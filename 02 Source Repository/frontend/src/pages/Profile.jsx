import { useEffect, useState } from 'react'

import { errorMessage } from '../api/client'
import { changePassword } from '../api/auth'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import { PageHeader } from '../components/ui/Feedback'
import { Input } from '../components/ui/Fields'
import StatCard from '../components/ui/StatCard'
import { titleCase } from '../lib/format'
import { useAuth } from '../store/auth'
import { useToast } from '../store/toast'

export default function Profile() {
  const user = useAuth((state) => state.user)
  const stats = useAuth((state) => state.stats)
  const refresh = useAuth((state) => state.refresh)
  const updateProfile = useAuth((state) => state.updateProfile)
  const push = useToast((state) => state.push)

  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    phone_number: user?.phone_number || '',
    mailing_address: user?.mailing_address || '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', confirm: '' })
  const [changing, setChanging] = useState(false)
  const [passwordError, setPasswordError] = useState('')

  useEffect(() => {
    refresh().catch(() => {})
  }, [refresh])

  const saveProfile = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      await updateProfile(form)
      push('Profile updated.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const savePassword = async (event) => {
    event.preventDefault()
    setPasswordError('')
    if (passwords.new_password !== passwords.confirm) {
      setPasswordError('New passwords do not match.')
      return
    }
    if (passwords.new_password.length < 8) {
      setPasswordError('New password must be at least 8 characters.')
      return
    }
    setChanging(true)
    try {
      await changePassword(passwords.current_password, passwords.new_password)
      push('Password changed.')
      setPasswords({ current_password: '', new_password: '', confirm: '' })
    } catch (err) {
      setPasswordError(errorMessage(err))
    } finally {
      setChanging(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Profile & security"
        description="Your identity, contact details and password."
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <StatCard label="Products" value={stats?.products ?? '—'} icon="box" tone="brand" />
        <StatCard label="Claims" value={stats?.claims ?? '—'} icon="clipboard" tone="neutral" />
        <StatCard label="Role" value={titleCase(user?.role)} icon="shield" tone="success" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profile details" subtitle={user?.user_id} action={<Badge tone="brand">{titleCase(user?.role)}</Badge>} />
          <CardBody>
            <form onSubmit={saveProfile} className="space-y-4">
              <Input
                label="Full name"
                value={form.full_name}
                onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
              />
              <Input
                label="Email"
                type="email"
                value={form.email}
                onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              />
              <Input
                label="Phone"
                value={form.phone_number}
                onChange={(event) => setForm((prev) => ({ ...prev, phone_number: event.target.value }))}
              />
              <Input
                label="Mailing address"
                value={form.mailing_address}
                onChange={(event) => setForm((prev) => ({ ...prev, mailing_address: event.target.value }))}
              />
              {error && <p className="text-xs text-status-danger">{error}</p>}
              <Button type="submit" loading={saving}>Save profile</Button>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Change password" subtitle="Minimum 8 characters" />
          <CardBody>
            <form onSubmit={savePassword} className="space-y-4">
              <Input
                label="Current password"
                type="password"
                autoComplete="current-password"
                value={passwords.current_password}
                onChange={(event) => setPasswords((prev) => ({ ...prev, current_password: event.target.value }))}
              />
              <Input
                label="New password"
                type="password"
                autoComplete="new-password"
                value={passwords.new_password}
                onChange={(event) => setPasswords((prev) => ({ ...prev, new_password: event.target.value }))}
              />
              <Input
                label="Confirm new password"
                type="password"
                autoComplete="new-password"
                value={passwords.confirm}
                onChange={(event) => setPasswords((prev) => ({ ...prev, confirm: event.target.value }))}
              />
              {passwordError && <p className="text-xs text-status-danger">{passwordError}</p>}
              <Button type="submit" variant="secondary" loading={changing}>Change password</Button>
            </form>
          </CardBody>
        </Card>
      </div>
    </>
  )
}


