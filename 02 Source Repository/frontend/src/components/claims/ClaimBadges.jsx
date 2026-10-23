import { DECISION_TONE, STATUS_TONE, WARRANTY_TONE } from '../../lib/constants'
import { titleCase } from '../../lib/format'
import { cn } from '../../lib/cn'
import Badge from '../ui/Badge'

export function StatusBadge({ status }) {
  if (!status) return null
  return (
    <Badge tone={STATUS_TONE[status] || 'neutral'} dot>
      {status}
    </Badge>
  )
}

export function DecisionBadge({ decision }) {
  if (!decision) return null
  return <Badge tone={DECISION_TONE[decision] || 'neutral'}>{decision}</Badge>
}

export function WarrantyBadge({ status }) {
  if (!status) return null
  return (
    <Badge tone={WARRANTY_TONE[status] || 'neutral'} dot>
      {status}
    </Badge>
  )
}

export function ConsistencyBadge({ status }) {
  const tone =
    status === 'Strong Match'
      ? 'success'
      : status === 'Acceptable Match'
        ? 'info'
        : status === 'Weak Match'
          ? 'warning'
          : status === 'Model Disagreement'
            ? 'danger'
            : 'neutral'
  return <Badge tone={tone}>{status || 'Unknown'}</Badge>
}

export function ConfidenceBar({ label, value, className = '' }) {
  const pct = Math.round((Number(value) || 0) * 100)
  const tone =
    pct >= 80 ? 'bg-status-success' : pct >= 60 ? 'bg-status-warning' : 'bg-status-danger'
  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="font-medium text-ink">{pct}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#F4F2EE]">
        <div className={cn('h-full rounded-full transition-all', tone)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function ClassBadge({ value }) {
  if (!value) return <Badge>Unknown</Badge>
  const tone =
    value === 'Valid Claim' ? 'success' : value === 'Invalid Claim' ? 'danger' : 'warning'
  return <Badge tone={tone}>{value}</Badge>
}

export function FaultLabel({ value }) {
  return <span>{titleCase(value)}</span>
}


