import { cn } from '../../utils/cn'
import Spinner from './Spinner'
import EmptyState from './EmptyState'

/**
 * Declarative table.
 *   columns: [{ key, header, render?(row), className?, headerClassName? }]
 *   data:    array of rows (must have stable `id` or pass rowKey)
 */
export default function Table({
  columns,
  data = [],
  loading = false,
  rowKey = 'id',
  onRowClick,
  emptyTitle = 'No records found',
  emptyDescription,
  emptyIcon,
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-800">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
          <thead className="bg-gray-50 dark:bg-gray-900/60">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400',
                    col.headerClassName,
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white dark:divide-gray-800 dark:bg-gray-900">
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-5 py-16">
                  <div className="flex justify-center text-brand-600">
                    <Spinner className="h-7 w-7" />
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-5 py-12">
                  <EmptyState
                    title={emptyTitle}
                    description={emptyDescription}
                    icon={emptyIcon}
                  />
                </td>
              </tr>
            ) : (
              data.map((row) => (
                <tr
                  key={row[rowKey]}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    'transition-colors',
                    onRowClick && 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50',
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        'px-5 py-3.5 text-sm text-gray-700 dark:text-gray-300',
                        col.className,
                      )}
                    >
                      {col.render ? col.render(row) : row[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
