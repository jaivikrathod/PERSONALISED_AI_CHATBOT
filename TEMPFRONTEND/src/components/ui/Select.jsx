import { forwardRef } from 'react'
import { cn } from '../../utils/cn'

const Select = forwardRef(function Select(
  { label, error, options = [], className, containerClassName, id, children, ...props },
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
      <select
        id={inputId}
        ref={ref}
        className={cn('input-base appearance-none pr-9', className)}
        {...props}
      >
        {children ||
          options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
      </select>
      {error && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
})

export default Select
