import { Outlet } from 'react-router-dom'
import { useSelector } from 'react-redux'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

/**
 * App shell: fixed sidebar (desktop) / drawer (mobile) + sticky topbar.
 * Pages render through <Outlet/>.
 */
export default function DashboardLayout() {
  const sidebarOpen = useSelector((s) => s.ui.sidebarOpen)

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
