import { Link, useLocation } from 'react-router-dom'
import { ChevronRightIcon, HomeIcon } from '@heroicons/react/20/solid'
import { ROUTE_LABELS, homePathForType } from '../../routes/navigation'
import useAuth from '../../hooks/useAuth'

export default function Breadcrumbs() {
  const { pathname } = useLocation()
  const { userType } = useAuth()
  const segments = pathname.split('/').filter(Boolean)
  const home = homePathForType(userType)

  return (
    <nav aria-label="Breadcrumb" className="hidden items-center gap-1.5 text-sm md:flex">
      <Link
        to={home}
        className="text-gray-400 transition hover:text-gray-600 dark:hover:text-gray-200"
        aria-label="Home"
      >
        <HomeIcon className="h-4 w-4" />
      </Link>
      {segments.map((seg, i) => {
        const to = '/' + segments.slice(0, i + 1).join('/')
        const isLast = i === segments.length - 1
        const label = ROUTE_LABELS[seg] || seg.replace(/[-_]/g, ' ')
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
