import { useDispatch } from 'react-redux'
import { Bars3Icon } from '@heroicons/react/24/outline'
import { toggleSidebar } from '../../redux/slices/uiSlice'
import Breadcrumbs from './Breadcrumbs'
import ThemeToggle from './ThemeToggle'
import ProfileDropdown from './ProfileDropdown'

export default function Topbar() {
  const dispatch = useDispatch()

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-gray-200 bg-white/80 px-4 backdrop-blur-md dark:border-gray-800 dark:bg-gray-900/80 sm:px-6">
      <button
        onClick={() => dispatch(toggleSidebar())}
        className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 lg:hidden"
        aria-label="Open sidebar"
      >
        <Bars3Icon className="h-5 w-5" />
      </button>

      <Breadcrumbs />

      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
        <div className="mx-1 hidden h-6 w-px bg-gray-200 dark:bg-gray-700 sm:block" />
        <ProfileDropdown />
      </div>
    </header>
  )
}
