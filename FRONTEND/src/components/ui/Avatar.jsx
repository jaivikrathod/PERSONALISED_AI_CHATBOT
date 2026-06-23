import { cn } from '../../utils/cn'
import { initials } from '../../utils/format'

const SIZES = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
}

const STATUS = {
  online: 'bg-emerald-500',
  offline: 'bg-gray-400',
  away: 'bg-amber-500',
}

export default function Avatar({ name, src, size = 'md', status, className }) {
  return (
    <span className={cn('relative inline-flex shrink-0', className)}>
      {src ? (
        <img
          src={src}
          alt={name}
          className={cn('rounded-full object-cover', SIZES[size])}
        />
      ) : (
        <span
          className={cn(
            'inline-flex items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-700 dark:bg-brand-500/20 dark:text-brand-300',
            SIZES[size],
          )}
        >
          {initials(name) || '?'}
        </span>
      )}
      {status && (
        <span
          className={cn(
            'absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full ring-2 ring-white dark:ring-gray-900',
            STATUS[status] || STATUS.offline,
          )}
        />
      )}
    </span>
  )
}
