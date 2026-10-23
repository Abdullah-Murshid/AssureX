import { cn } from '../../lib/cn'

export default function Card({ children, className = '', as: Tag = 'div', ...props }) {
  return (
    <Tag
      className={cn('rounded-2xl border border-line bg-surface shadow-card-soft', className)}
      {...props}
    >
      {children}
    </Tag>
  )
}

export function CardHeader({ title, subtitle, action, className = '' }) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-3 border-b border-line/70 px-5 py-4',
        className,
      )}
    >
      <div>
        <h2 className="type-card-title">{title}</h2>
        {subtitle && <p className="mt-0.5 text-[12px] text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function CardBody({ children, className = '', ...props }) {
  return (
    <div className={cn('p-5', className)} {...props}>
      {children}
    </div>
  )
}
