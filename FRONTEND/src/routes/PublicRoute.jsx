import { Navigate, Outlet } from 'react-router-dom'
import useAuth from '../hooks/useAuth'

/** Keeps authenticated users out of /login. */
export default function PublicRoute() {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
