import { formatDateTime, titleCase } from '../../lib/format'
import { cn } from '../../lib/cn'
import Icon from '../ui/Icon'

const TONE = {
  Draft: 'border-line bg-surface text-muted-light',
  Submitted: 'border-brand-500/30 bg-tint text-brand-500',
  'Under Evaluation': 'border-status-warning/30 bg-status-warning/[0.07] text-status-warning',
  'Manual Review': 'border-status-warning/30 bg-status-warning/[0.07] text-status-warning',
  'Request More Info': 'border-status-warning/30 bg-status-warning/[0.07] text-status-warning',
  Approved: 'border-status-success/30 bg-status-success/[0.07] text-status-success',
  Rejected: 'border-status-danger/30 bg-status-danger/[0.07] text-status-danger',
  Closed: 'border-line bg-surface-alt text-muted',
}

const ICON = {
  Draft: 'file',
  Submitted: 'clipboard',
  'Under Evaluation': 'clock',
  'Manual Review': 'shield',
  'Request More Info': 'alert',
  Approved: 'check',
  Rejected: 'alert',
  Closed: 'check',
}

export default function StatusTimeline({ history = [] }) {
  if (!history.length) {
    return <p className="text-xs text-muted-light">No status history recorded.</p>
  }

  return (
    <ol className="relative ml-1 space-y-5 border-l border-line pl-5">
      {history.map((row, index) => {
        const last = index === history.length - 1
        const tone = TONE[row.to_status] || 'border-line bg-surface-alt text-muted'
        return (
          <li key={`${row.id}-${index}`} className={cn('relative', last && 'pb-0')}>
            <span
              className={cn(
                'absolute -left-[27px] flex h-5 w-5 items-center justify-center rounded-full border',
                tone,
              )}
            >
              <Icon name={ICON[row.to_status] || 'clock'} size={11} />
            </span>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-[12px] font-medium text-ink">
                {row.from_status ? `${row.from_status} → ${row.to_status}` : row.to_status}
              </p>
              <time className="text-[10.5px] text-muted-light">{formatDateTime(row.created_at)}</time>
            </div>
            <p className="mt-0.5 text-[10.5px] text-muted-light">
              {row.actor_role ? titleCase(row.actor_role) : 'System'}
              {row.actor_user_id ? ` · ${row.actor_user_id}` : ''}
            </p>
            {row.note && <p className="mt-1 text-[11px] leading-relaxed text-muted">{row.note}</p>}
          </li>
        )
      })}
    </ol>
  )
}
