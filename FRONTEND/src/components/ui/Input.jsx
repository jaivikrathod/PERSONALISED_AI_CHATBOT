import { forwardRef } from 'react'
import { cn } from '../../utils/cn'

/**
 * Label + input + error, wired to work with React Hook Form's register().
 * Pass `icon` for a leading icon element.
 */
const Input = forwardRef(function Input(
  { label, error, icon, className, containerClassName, id, ...props },
  ref,
) {
  const inputId = id || props.name
  return (
    <div className={cn('w-full', containerClassName)}>
      {label && (
        <label
          htmlFor={inputId}
          className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
            {icon}
          </span>
        )}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            'input-base',
            icon && 'pl-10',
            error &&
              'border-red-400 focus:border-red-500 focus:ring-red-500/30 dark:border-red-500/60',
            className,
          )}
          {...props}
        />
      </div>
      {error && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
})

export default Input
