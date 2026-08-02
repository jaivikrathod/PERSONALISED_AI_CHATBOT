import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import useAuth from '../../hooks/useAuth'
import { fetchUnanswered } from '../../redux/slices/unansweredSlice'

/**
 * App shell: fixed sidebar (desktop) / drawer (mobile) + sticky topbar.
 * Pages render through <Outlet/>.
 */
export default function DashboardLayout() {
  const dispatch = useDispatch()
  const sidebarOpen = useSelector((s) => s.ui.sidebarOpen)
  const { companyId, canManageUsers } = useAuth()

  // Powers the "Unanswered" badge in the sidebar; the page itself refetches.
  useEffect(() => {
    if (companyId && canManageUsers) dispatch(fetchUnanswered(companyId))
  }, [dispatch, companyId, canManageUsers])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar mobileOpen={sidebarOpen} />
      <div className="lg:pl-64">
        <Topbar />
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
