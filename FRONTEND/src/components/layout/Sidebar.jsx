import { NavLink } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { XMarkIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { NAV_ITEMS } from '../../routes/navigation'
import { setSidebar } from '../../redux/slices/uiSlice'
import { cn } from '../../utils/cn'

function NavItems({ onNavigate }) {
  return (
    <nav className="flex-1 space-y-1 px-3 py-4">
      {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              isActive
                ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100',
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                className={cn(
                  'h-5 w-5 shrink-0',
                  isActive
                    ? 'text-brand-600 dark:text-brand-400'
                    : 'text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300',
                )}
              />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex h-16 items-center gap-2.5 border-b border-gray-100 px-5 dark:border-gray-800">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white shadow-sm">
        <SparklesIcon className="h-5 w-5" />
      </span>
      <span className="text-lg font-bold tracking-tight text-gray-900 dark:text-white">
        SupportAI
      </span>
    </div>
  )
}

export default function Sidebar({ mobileOpen }) {
  const dispatch = useDispatch()
  const close = () => dispatch(setSidebar(false))

  return (
    <>
      {/* Desktop — fixed */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:flex lg:w-64 lg:flex-col lg:border-r lg:border-gray-200 lg:bg-white lg:dark:border-gray-800 lg:dark:bg-gray-900">
        <Brand />
        <NavItems />
        <UpgradeCard />
      </aside>

      {/* Mobile — drawer */}
      <div
        className={cn(
          'fixed inset-0 z-40 lg:hidden',
          mobileOpen ? 'pointer-events-auto' : 'pointer-events-none',
        )}
      >
        <div
          className={cn(
            'absolute inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity',
            mobileOpen ? 'opacity-100' : 'opacity-0',
          )}
          onClick={close}
        />
        <aside
          className={cn(
            'absolute inset-y-0 left-0 flex w-72 flex-col bg-white shadow-xl transition-transform dark:bg-gray-900',
            mobileOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <div className="flex items-center justify-between border-b border-gray-100 pr-3 dark:border-gray-800">
            <Brand />
            <button
              onClick={close}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
          <NavItems onNavigate={close} />
          <UpgradeCard />
        </aside>
      </div>
    </>
  )
}

function UpgradeCard() {
  return (
    <div className="p-3">
      <div className="rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 p-4 text-white">
        <p className="text-sm font-semibold">Upgrade to Pro</p>
        <p className="mt-1 text-xs text-white/80">
          Unlock advanced AI routing & unlimited agents.
        </p>
        <button className="mt-3 w-full rounded-lg bg-white/15 py-1.5 text-xs font-medium backdrop-blur transition hover:bg-white/25">
          Upgrade
        </button>
      </div>
    </div>
  )
}
