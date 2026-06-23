import { Link, useLocation } from 'react-router-dom'
import { ChevronRightIcon, HomeIcon } from '@heroicons/react/20/solid'
import { ROUTE_LABELS } from '../../routes/navigation'

export default function Breadcrumbs() {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean)

  return (
    <nav aria-label="Breadcrumb" className="hidden items-center gap-1.5 text-sm md:flex">
      <Link
        to="/dashboard"
        className="text-gray-400 transition hover:text-gray-600 dark:hover:text-gray-200"
      >
        <HomeIcon className="h-4 w-4" />
      </Link>
      {segments.map((seg, i) => {
        const to = '/' + segments.slice(0, i + 1).join('/')
        const isLast = i === segments.length - 1
        const label = ROUTE_LABELS[seg] || seg.replace(/-/g, ' ')
        return (
          <span key={to} className="flex items-center gap-1.5">
            <ChevronRightIcon className="h-4 w-4 text-gray-300 dark:text-gray-600" />
            {isLast ? (
              <span className="font-medium capitalize text-gray-700 dark:text-gray-200">
                {label}
              </span>
            ) : (
              <Link
                to={to}
                className="capitalize text-gray-400 transition hover:text-gray-600 dark:hover:text-gray-200"
              >
                {label}
              </Link>
            )}
          </span>
        )
      })}
    </nav>
  )
}
