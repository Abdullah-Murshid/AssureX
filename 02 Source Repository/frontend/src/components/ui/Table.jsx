import { cn } from '../../lib/cn'

export function Table({ children, className = '', minWidth = 'min-w-[720px]' }) {
  return (
    <div className="overflow-x-auto">
      <table className={cn('w-full text-left text-[13px]', minWidth, className)}>{children}</table>
    </div>
  )
}

export function THead({ children }) {
  return (
    <thead className="border-b border-line bg-[#FAFAF8] text-[10.5px] font-medium tracking-[0.08em] text-muted-light uppercase">
      {children}
    </thead>
  )
}

export function TBody({ children }) {
  return <tbody className="divide-y divide-line/60">{children}</tbody>
}

export function Th({ children, className = '' }) {
  return <th className={cn('px-4 py-2.5 font-medium whitespace-nowrap', className)}>{children}</th>
}

export function Td({ children, className = '' }) {
  return <td className={cn('px-4 py-3 align-middle text-ink/80', className)}>{children}</td>
}
