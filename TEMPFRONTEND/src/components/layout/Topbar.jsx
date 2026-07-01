import { useDispatch } from 'react-redux'
import { Bars3Icon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { toggleSidebar } from '../../redux/slices/uiSlice'
import Breadcrumbs from './Breadcrumbs'
import ThemeToggle from './ThemeToggle'
import NotificationsDropdown from './NotificationsDropdown'
import ProfileDropdown from './ProfileDropdown'

export default function Topbar() {
  const dispatch = useDispatch()

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-gray-200 bg-white/80 px-4 backdrop-blur-md dark:border-gray-800 dark:bg-gray-900/80 sm:px-6">
      {/* Mobile menu button */}
      <button
        onClick={() => dispatch(toggleSidebar())}
        className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 lg:hidden"
        aria-label="Open sidebar"
      >
        <Bars3Icon className="h-5 w-5" />
      </button>

      <Breadcrumbs />

      {/* Global search (decorative trigger) */}
      <div className="ml-auto hidden md:block">
        <div className="relative">
          <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            placeholder="Search…"
            className="h-9 w-56 rounded-lg border border-gray-200 bg-gray-50 pl-9 pr-3 text-sm text-gray-700 placeholder:text-gray-400 focus:border-brand-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
          />
        </div>
      </div>

      <div className="ml-auto flex items-center gap-1 md:ml-0">
        <ThemeToggle />
        <NotificationsDropdown />
        <div className="mx-1 hidden h-6 w-px bg-gray-200 dark:bg-gray-700 sm:block" />
        <ProfileDropdown />
      </div>
    </header>
  )
}
