import { forwardRef } from 'react'
import { cn } from '../../utils/cn'

const Textarea = forwardRef(function Textarea(
  { label, error, className, containerClassName, id, rows = 4, ...props },
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
      <textarea
        id={inputId}
        ref={ref}
        rows={rows}
        className={cn(
          'input-base resize-y',
          error && 'border-red-400 focus:border-red-500 focus:ring-red-500/30',
          className,
        )}
        {...props}
      />
      {error && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
})

export default Textarea
