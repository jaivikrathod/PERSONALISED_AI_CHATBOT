import { useEffect, useRef, useState } from 'react'
import { cn } from '../../utils/cn'

/**
 * Lightweight click-outside dropdown.
 *   <Dropdown trigger={<Button/>}>
 *     <Dropdown.Item onClick={…}>…</Dropdown.Item>
 *   </Dropdown>
 */
export default function Dropdown({ trigger, align = 'right', width = 'w-56', children }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <div onClick={() => setOpen((o) => !o)}>{trigger}</div>
      {open && (
        <div
          className={cn(
            'absolute z-40 mt-2 overflow-hidden rounded-xl border border-gray-200 bg-white py-1 shadow-card-hover animate-slide-up dark:border-gray-800 dark:bg-gray-900',
            width,
            align === 'right' ? 'right-0' : 'left-0',
          )}
          onClick={() => setOpen(false)}
        >
          {children}
        </div>
      )}
    </div>
  )
}

Dropdown.Item = function DropdownItem({ icon: Icon, danger, className, children, ...props }) {
  return (
    <button
      className={cn(
        'flex w-full items-center gap-2.5 px-3.5 py-2 text-left text-sm transition-colors',
        danger
          ? 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10'
          : 'text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800',
        className,
      )}
      {...props}
    >
      {Icon && <Icon className="h-4 w-4 shrink-0" />}
      {children}
    </button>
  )
}

Dropdown.Divider = function DropdownDivider() {
  return <div className="my-1 h-px bg-gray-100 dark:bg-gray-800" />
}
