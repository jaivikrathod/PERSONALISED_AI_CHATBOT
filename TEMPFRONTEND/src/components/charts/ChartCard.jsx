import { cn } from '../../utils/cn'

/** Card wrapper for any chart with a title + optional toolbar. */
export default function ChartCard({ title, subtitle, action, className, children }) {
  return (
    <div className={cn('card-base p-5', className)}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
            {title}
          </h3>
          {subtitle && (
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          )}
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}
