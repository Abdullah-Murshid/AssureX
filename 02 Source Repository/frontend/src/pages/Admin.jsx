import { useEffect, useMemo, useState } from 'react'

import {
  analytics as fetchAnalytics,
  auditLogs,
  exportClaimsCsv,
  getSettings,
  listPolicies,
  savePolicy,
  updateSettings,
} from '../api/admin'
import { errorMessage } from '../api/client'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import { PageHeader, Spinner, Tabs } from '../components/ui/Feedback'
import { Input } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import Pagination from '../components/ui/Pagination'
import StatCard from '../components/ui/StatCard'
import { Table, TBody, Td, Th, THead } from '../components/ui/Table'
import { formatDateTime, formatPercent, titleCase } from '../lib/format'
import { useToast } from '../store/toast'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'policies', label: 'Policies' },
  { id: 'audit', label: 'Audit log' },
  { id: 'settings', label: 'Settings' },
]

const SETTING_FIELDS = [
  ['model_version', 'Model version', 'text'],
  ['uncertainty_threshold', 'Uncertainty threshold', 'number'],
  ['strong_match_threshold', 'Strong match threshold', 'number'],
  ['acceptable_match_threshold', 'Acceptable match threshold', 'number'],
  ['warranty_alert_days', 'Warranty alert days', 'number'],
  ['disagreement_alert_rate', 'Disagreement alert rate', 'number'],
  ['manual_review_spike_rate', 'Manual review spike rate', 'number'],
]

export default function Admin() {
  const push = useToast((state) => state.push)
  const [tab, setTab] = useState('overview')

  const exportCsv = () =>
    exportClaimsCsv()
      .then(() => push('Claims CSV downloaded.'))
      .catch((err) => push(errorMessage(err), 'error'))

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="System control"
        description="Policy configuration, monitoring, audit trail and runtime settings."
        actions={
          <Button variant="secondary" icon="download" onClick={exportCsv}>
            Export claims CSV
          </Button>
        }
      />
      <Tabs tabs={TABS} value={tab} onChange={setTab} className="mb-6 w-fit" />
      {tab === 'overview' && <Overview />}
      {tab === 'policies' && <Policies />}
      {tab === 'audit' && <AuditLog />}
      {tab === 'settings' && <Settings />}
    </>
  )
}

function DistributionBar({ label, value, total, tone = 'brand' }) {
  const pct = total ? Math.round((value / total) * 100) : 0
  const color =
    tone === 'success'
      ? 'bg-status-success'
      : tone === 'danger'
        ? 'bg-status-danger'
        : tone === 'warning'
          ? 'bg-status-warning'
          : 'bg-brand-500'
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="text-ink">{value} · {pct}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#F4F2EE]">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Overview() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchAnalytics()
      .then((result) => active && setData(result))
      .catch((err) => active && setError(errorMessage(err)))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  if (loading) return <Spinner label="Loading analytics…" />
  if (error) {
    return <p className="rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">{error}</p>
  }

  const totals = data.totals || {}
  const decisions = data.decision_distribution || {}
  const statuses = Object.entries(data.status_distribution || {}).sort((a, b) => b[1] - a[1])
  const categories = Object.entries(data.category_distribution || {})
  const monitoring = data.monitoring || {}
  const months = Object.entries(data.monthly_claims || {}).slice(-6)

  return (
    <div className="space-y-6">
      <div className="grid animate-enter-up gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Claims" value={totals.claims ?? 0} hint={`${totals.model_disagreements ?? 0} model disagreements`} icon="clipboard" />
        <StatCard label="Products" value={totals.products ?? 0} icon="box" tone="neutral" />
        <StatCard label="Documents" value={totals.documents ?? 0} icon="file" tone="neutral" />
        <StatCard label="Audit events" value={totals.audit_events ?? 0} icon="shield" tone="success" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Decision distribution" subtitle="Final adjudication outcomes" />
          <CardBody className="space-y-4">
            <DistributionBar label="Likely valid" value={decisions.likely_valid ?? 0} total={totals.claims} tone="success" />
            <DistributionBar label="Likely invalid" value={decisions.likely_invalid ?? 0} total={totals.claims} tone="danger" />
            <DistributionBar label="Manual review" value={decisions.manual_review ?? 0} total={totals.claims} tone="warning" />
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Monitoring" subtitle="Operational health flags" />
          <CardBody className="space-y-3">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl border border-line/70 bg-[#FAFAF8] p-3">
                <p className="text-muted-light">Disagreement rate</p>
                <p className="mt-1 text-lg font-semibold text-ink">{formatPercent(monitoring.disagree_rate)}</p>
              </div>
              <div className="rounded-xl border border-line/70 bg-[#FAFAF8] p-3">
                <p className="text-muted-light">Manual review rate</p>
                <p className="mt-1 text-lg font-semibold text-ink">{formatPercent(monitoring.review_rate)}</p>
              </div>
              <div className="rounded-xl border border-line/70 bg-[#FAFAF8] p-3">
                <p className="text-muted-light">Duplicate hashes</p>
                <p className="mt-1 text-lg font-semibold text-ink">{monitoring.duplicate_hashes ?? 0}</p>
              </div>
              <div className="rounded-xl border border-line/70 bg-[#FAFAF8] p-3">
                <p className="text-muted-light">Claims analysed</p>
                <p className="mt-1 text-lg font-semibold text-ink">{monitoring.total ?? 0}</p>
              </div>
            </div>
            {monitoring.flags?.length ? (
              monitoring.flags.map((flag) => (
                <p key={flag} className="flex gap-2 rounded-lg border border-status-warning/25 bg-status-warning/10 px-3 py-2 text-[11px] text-status-warning">
                  <Icon name="alert" size={13} className="mt-0.5 shrink-0" /> {flag}
                </p>
              ))
            ) : (
              <p className="text-[11px] text-status-success">No monitoring flags.</p>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader title="Statuses" />
          <CardBody className="space-y-2 text-xs">
            {statuses.length ? statuses.map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <span className="text-muted">{status}</span>
                <Badge>{count}</Badge>
              </div>
            )) : <p className="text-muted-light">No claims yet.</p>}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Categories" />
          <CardBody className="space-y-2 text-xs">
            {categories.map(([category, count]) => (
              <div key={category} className="flex items-center justify-between">
                <span className="text-muted">{titleCase(category)}</span>
                <Badge>{count}</Badge>
              </div>
            ))}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Recent months" subtitle="Claims per submission month" />
          <CardBody className="space-y-2 text-xs">
            {months.length ? months.map(([month, count]) => (
              <div key={month} className="flex items-center justify-between">
                <span className="text-muted">{month}</span>
                <Badge tone="brand">{count}</Badge>
              </div>
            )) : <p className="text-muted-light">No submissions yet.</p>}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}

function Policies() {
  const push = useToast((state) => state.push)
  const [policies, setPolicies] = useState(null)
  const [selected, setSelected] = useState('electronics')
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listPolicies()
      .then((result) => {
        setPolicies(result.policies || {})
        const first = result.categories?.[0] || 'electronics'
        setSelected(first)
        setText(JSON.stringify(result.policies?.[first] || {}, null, 2))
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  const choose = (category) => {
    setSelected(category)
    setText(JSON.stringify(policies?.[category] || {}, null, 2))
    setError('')
  }

  const save = async () => {
    setError('')
    let parsed
    try {
      parsed = JSON.parse(text)
    } catch {
      setError('Invalid JSON — fix the syntax before saving.')
      return
    }
    setSaving(true)
    try {
      const result = await savePolicy(selected, parsed)
      setPolicies((prev) => ({ ...prev, [selected]: result.policy }))
      push(`${titleCase(selected)} policy saved.`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Spinner label="Loading policies…" />
  if (!policies) {
    return <p className="rounded-xl border border-status-danger/30 bg-status-danger/10 px-4 py-3 text-sm text-status-danger">{error}</p>
  }

  return (
    <div className="grid gap-6 lg:grid-cols-4">
      <Card className="lg:col-span-1">
        <CardHeader title="Categories" />
        <CardBody className="space-y-1">
          {Object.keys(policies).map((category) => (
            <button
              key={category}
              type="button"
              onClick={() => choose(category)}
              className={`w-full rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                selected === category
                  ? 'bg-tint text-brand-500'
                  : 'text-muted hover:bg-[#F4F2EE] hover:text-ink'
              }`}
            >
              {titleCase(category)}
            </button>
          ))}
        </CardBody>
      </Card>

      <Card className="lg:col-span-3">
        <CardHeader
          title={`${titleCase(selected)} policy`}
          subtitle="Edit the JSON policy consumed by the rule engine"
          action={
            <Button size="sm" loading={saving} onClick={save}>
              Save policy
            </Button>
          }
        />
        <CardBody>
          {error && <p className="mb-3 text-xs text-status-danger">{error}</p>}
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            spellCheck={false}
            rows={26}
            className="w-full rounded-xl border border-line bg-[#FAFAF8] p-4 text-[12px] leading-relaxed text-ink focus:border-brand-500 focus:outline-none"
          />
        </CardBody>
      </Card>
    </div>
  )
}

function AuditLog() {
  const [filters, setFilters] = useState({ action: '', user_id: '', claim_id: '' })
  const [applied, setApplied] = useState({ action: '', user_id: '', claim_id: '' })
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const query = useMemo(
    () => ({
      action: applied.action || undefined,
      user_id: applied.user_id || undefined,
      claim_id: applied.claim_id || undefined,
      page,
      per_page: 15,
    }),
    [applied, page],
  )

  useEffect(() => {
    let active = true
    setLoading(true)
    auditLogs(query)
      .then((result) => active && setData(result))
      .catch((err) => active && setError(errorMessage(err)))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [query])

  return (
    <Card>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          setPage(1)
          setApplied(filters)
        }}
        className="grid gap-3 border-b border-line/70 p-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <Input label="Action" placeholder="AI Inference" value={filters.action} onChange={(event) => setFilters((prev) => ({ ...prev, action: event.target.value }))} />
        <Input label="User ID" placeholder="USR-0001" value={filters.user_id} onChange={(event) => setFilters((prev) => ({ ...prev, user_id: event.target.value }))} />
        <Input label="Claim ID" placeholder="CLM-2026-…" value={filters.claim_id} onChange={(event) => setFilters((prev) => ({ ...prev, claim_id: event.target.value }))} />
        <div className="flex items-end">
          <Button type="submit" size="sm" className="w-full">Filter</Button>
        </div>
      </form>

      {error && <p className="p-4 text-xs text-status-danger">{error}</p>}

      {loading && !data ? (
        <Spinner label="Loading audit trail…" />
      ) : data?.items?.length ? (
        <>
          <Table minWidth="min-w-[900px]">
            <THead>
              <tr>
                <Th>Timestamp</Th>
                <Th>Action</Th>
                <Th>Actor</Th>
                <Th>Entity</Th>
                <Th>Claim</Th>
                <Th>Details</Th>
              </tr>
            </THead>
            <TBody>
              {data.items.map((log) => (
                <tr key={log.id}>
                  <Td className="whitespace-nowrap">{formatDateTime(log.timestamp)}</Td>
                  <Td><Badge tone="brand">{log.action}</Badge></Td>
                  <Td>{log.performed_by}</Td>
                  <Td>
                    <p>{log.entity_type}</p>
                    <p className="text-[11px] text-muted-light">{log.entity_id}</p>
                  </Td>
                  <Td className="text-[11px] text-brand-500">{log.claim_id || '—'}</Td>
                  <Td>
                    <code className="block max-w-[260px] truncate text-[11px] text-muted-light">
                      {JSON.stringify(log.details)}
                    </code>
                  </Td>
                </tr>
              ))}
            </TBody>
          </Table>
          <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onPage={setPage} />
        </>
      ) : (
        <p className="p-8 text-center text-xs text-muted-light">No audit events match the filters.</p>
      )}
    </Card>
  )
}

function Settings() {
  const push = useToast((state) => state.push)
  const [values, setValues] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getSettings()
      .then((result) => setValues(result.settings || {}))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    const payload = {}
    SETTING_FIELDS.forEach(([key, , type]) => {
      payload[key] = type === 'number' ? Number(values[key]) : values[key]
    })
    try {
      const result = await updateSettings(payload)
      setValues(result.settings || values)
      push('Settings saved.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Spinner label="Loading settings…" />
  if (!values) return <p className="text-sm text-status-danger">{error}</p>

  return (
    <form onSubmit={save} className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader title="Runtime thresholds" subtitle="Applied to adjudication and monitoring" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          {SETTING_FIELDS.map(([key, label, type]) => (
            <Input
              key={key}
              label={label}
              type={type}
              step={type === 'number' ? '0.01' : undefined}
              value={values[key] ?? ''}
              onChange={(event) => setValues((prev) => ({ ...prev, [key]: event.target.value }))}
            />
          ))}
        </CardBody>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardBody className="space-y-2 text-xs text-muted">
            <p className="text-sm font-medium text-ink">How these are used</p>
            <p>Thresholds drive the dual-model consistency labels and manual-review escalation.</p>
            <p>Changes are written to <code className="text-ink/80">config/settings.yaml</code>.</p>
          </CardBody>
        </Card>
        {error && <p className="rounded-lg border border-status-danger/30 bg-status-danger/10 px-3 py-2 text-xs text-status-danger">{error}</p>}
        <Button type="submit" loading={saving} className="w-full">Save settings</Button>
      </div>
    </form>
  )
}



