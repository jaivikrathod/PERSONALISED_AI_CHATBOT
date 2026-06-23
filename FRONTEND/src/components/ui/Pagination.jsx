import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/20/solid'
import { cn } from '../../utils/cn'

/** Compact pagination with a sliding window of page numbers. */
export default function Pagination({ page, pageSize, total, onChange }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (totalPages <= 1) return null

  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  const pages = []
  const from = Math.max(1, page - 1)
  const to = Math.min(totalPages, page + 1)
  if (from > 1) pages.push(1, '…')
  for (let i = from; i <= to; i++) pages.push(i)
  if (to < totalPages) pages.push('…', totalPages)

  const btn =
    'inline-flex h-9 min-w-9 items-center justify-center rounded-lg px-2 text-sm font-medium transition'

  return (
    <div className="flex flex-col items-center justify-between gap-3 px-1 py-3 sm:flex-row">
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Showing <span className="font-medium text-gray-700 dark:text-gray-200">{start}</span>–
        <span className="font-medium text-gray-700 dark:text-gray-200">{end}</span> of{' '}
        <span className="font-medium text-gray-700 dark:text-gray-200">{total}</span>
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          className={cn(btn, 'text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:hover:bg-gray-800')}
        >
          <ChevronLeftIcon className="h-4 w-4" />
        </button>
        {pages.map((p, i) =>
          p === '…' ? (
            <span key={`e${i}`} className="px-1 text-gray-400">
              …
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onChange(p)}
              className={cn(
                btn,
                p === page
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800',
              )}
            >
              {p}
            </button>
          ),
        )}
        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          className={cn(btn, 'text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:hover:bg-gray-800')}
        >
          <ChevronRightIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
