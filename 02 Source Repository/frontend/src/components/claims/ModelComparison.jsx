import { formatPercent } from '../../lib/format'
import Badge from '../ui/Badge'
import Card, { CardHeader } from '../ui/Card'
import { ClassBadge, ConfidenceBar, ConsistencyBadge } from './ClaimBadges'

function ModelPanel({ title, subtitle, model, comparison }) {
  const predicted = model === 'python' ? comparison?.python_predicted_class : comparison?.vision_predicted_class
  const confidence =
    model === 'python' ? comparison?.python_top_confidence : comparison?.vision_top_confidence
  const probabilities =
    model === 'python' ? comparison?.python_probabilities : comparison?.vision_probabilities
  const accent = model === 'python' ? 'text-brand-500' : 'text-brand-500'

  return (
    <div className="rounded-xl border border-line bg-[#FAFAF8] p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className={`text-xs font-semibold tracking-wide uppercase ${accent}`}>{title}</p>
          <p className="mt-0.5 text-[11px] text-muted-light">{subtitle}</p>
        </div>
        <ClassBadge value={predicted} />
      </div>
      <p className="mt-3 font-display text-[30px] font-normal text-ink">{formatPercent(confidence)}</p>
      <ConfidenceBar label="Top confidence" value={confidence} className="mt-2" />
      {probabilities && (
        <dl className="mt-3 space-y-1.5 border-t border-line/70 pt-3">
          {Object.entries(probabilities).map(([label, value]) => (
            <div key={label} className="flex items-center justify-between text-[11px]">
              <dt className="text-muted-light">{label}</dt>
              <dd className="text-ink/80">{formatPercent(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  )
}

export default function ModelComparison({ comparison }) {
  if (!comparison) return null
  const difference = Math.abs(Number(comparison.confidence_difference) || 0)

  return (
    <Card>
      <CardHeader
        title="Dual-model adjudication"
        subtitle="Python tabular model vs. Teachable Machine vision model"
        action={<ConsistencyBadge status={comparison.consistency_status} />}
      />
      <div className="grid gap-3 p-5 md:grid-cols-2">
        <ModelPanel
          title="Python ML"
          subtitle="XGBoost tabular classifier"
          model="python"
          comparison={comparison}
        />
        <ModelPanel
          title="Vision (GTM)"
          subtitle="Summary card image classifier"
          model="vision"
          comparison={comparison}
        />
        <div className="md:col-span-2">
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-[#FAFAF8] px-4 py-3 text-xs text-muted">
            <span>
              Confidence difference:{' '}
              <strong className="text-ink">{formatPercent(difference, 2)}</strong>
            </span>
            <span className="hidden h-3 w-px bg-[#F4F2EE] sm:block" />
            <span className="flex-1">{comparison.status_description}</span>
            <Badge tone={comparison.classes_match ? 'success' : 'danger'}>
              {comparison.classes_match ? 'Classes agree' : 'Classes differ'}
            </Badge>
          </div>
        </div>
      </div>
    </Card>
  )
}


