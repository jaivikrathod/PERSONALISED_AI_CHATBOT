import { cn } from '../../utils/cn'

export default function Card({ className, children, ...props }) {
  return (
    <div className={cn('card-base', className)} {...props}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action, className }) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-4 border-b border-gray-100 px-5 py-4 dark:border-gray-800',
        className,
      )}
    >
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
  )
}

export function CardBody({ className, children }) {
  return <div className={cn('p-5', className)}>{children}</div>
}
