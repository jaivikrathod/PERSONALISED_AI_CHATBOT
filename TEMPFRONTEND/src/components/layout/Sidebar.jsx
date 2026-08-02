import { NavLink } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { navItemsForType } from '../../routes/navigation'
import { setSidebar } from '../../redux/slices/uiSlice'
import useAuth from '../../hooks/useAuth'
import { cn } from '../../utils/cn'

function NavItems({ items, badges, onNavigate }) {
  return (
    <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
      {items.map(({ label, to, icon: Icon, badge }) => {
        const count = badge ? badges[badge] : 0
        return (
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
                <span className="flex-1">{label}</span>
                {count > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1.5 text-[10px] font-bold text-white">
                    {count}
                  </span>
                )}
              </>
            )}
          </NavLink>
        )
      })}
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

function CompanyCard({ name }) {
  if (!name) return null
  return (
    <div className="p-3">
      <div className="rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 p-4 text-white">
        <p className="text-xs font-medium text-white/70">Workspace</p>
        <p className="mt-0.5 truncate text-sm font-semibold">{name}</p>
      </div>
    </div>
  )
}

export default function Sidebar({ mobileOpen }) {
  const dispatch = useDispatch()
  const { user, userType } = useAuth()
  const unansweredCount = useSelector((s) => s.unanswered.items.length)

  const items = navItemsForType(userType)
  const badges = { unanswered: unansweredCount }
  const close = () => dispatch(setSidebar(false))

  return (
    <>
      {/* Desktop — fixed */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:flex lg:w-64 lg:flex-col lg:border-r lg:border-gray-200 lg:bg-white lg:dark:border-gray-800 lg:dark:bg-gray-900">
        <Brand />
        <NavItems items={items} badges={badges} />
        <CompanyCard name={user?.company_name} />
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
              aria-label="Close sidebar"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
          <NavItems items={items} badges={badges} onNavigate={close} />
          <CompanyCard name={user?.company_name} />
        </aside>
      </div>
    </>
  )
}
