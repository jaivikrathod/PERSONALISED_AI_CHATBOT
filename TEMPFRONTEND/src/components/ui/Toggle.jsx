import { cn } from '../../utils/cn'

export default function Toggle({ checked, onChange, label, description, disabled }) {
  return (
    <label className={cn('flex items-center justify-between gap-4', disabled && 'opacity-60')}>
      {(label || description) && (
        <span>
          {label && (
            <span className="block text-sm font-medium text-gray-700 dark:text-gray-200">
              {label}
            </span>
          )}
          {description && (
            <span className="block text-xs text-gray-500 dark:text-gray-400">
              {description}
            </span>
          )}
        </span>
      )}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40',
          checked ? 'bg-brand-600' : 'bg-gray-300 dark:bg-gray-700',
        )}
      >
        <span
          className={cn(
            'inline-block h-5 w-5 translate-y-0.5 rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-[22px]' : 'translate-x-0.5',
          )}
        />
      </button>
    </label>
  )
}
