import Icon from './Icon'

export default function Pagination({ page = 1, totalPages = 1, total = 0, onPage }) {
  if (!total) return null
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line/70 px-4 py-3 text-[12px] text-muted">
      <span>
        Page <span className="font-medium text-ink">{page}</span> of{' '}
        <span className="font-medium text-ink">{Math.max(totalPages, 1)}</span> · {total} total
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-line bg-surface px-2.5 transition-colors duration-200 hover:border-line-input hover:bg-surface-alt disabled:opacity-40"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          <Icon name="chevronLeft" size={13} /> Prev
        </button>
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-line bg-surface px-2.5 transition-colors duration-200 hover:border-line-input hover:bg-surface-alt disabled:opacity-40"
          disabled={page >= totalPages}
          onClick={() => onPage(page + 1)}
        >
          Next <Icon name="chevronRight" size={13} />
        </button>
      </div>
    </div>
  )
}
