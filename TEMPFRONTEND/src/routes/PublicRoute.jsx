import { Navigate, Outlet } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { homePathForType } from './navigation'

/** Keeps authenticated users out of /login and /register. */
export default function PublicRoute() {
  const { isAuthenticated, userType } = useAuth()
  if (isAuthenticated) return <Navigate to={homePathForType(userType)} replace />
  return <Outlet />
}
