import { cn } from '../../utils/cn'

const TONES = {
  gray: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  green: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400',
  red: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
  yellow: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400',
  blue: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400',
  brand: 'bg-brand-100 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300',
}

// Map domain statuses to tones so callers can pass status directly.
export const STATUS_TONE = {
  open: 'blue',
  pending: 'yellow',
  resolved: 'green',
  escalated: 'red',
  active: 'green',
  inactive: 'gray',
  online: 'green',
  offline: 'gray',
}

export default function Badge({ tone = 'gray', dot = false, className, children }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
        TONES[tone] || TONES.gray,
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}
