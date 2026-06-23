import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import useAuth from '../hooks/useAuth'
import { fetchCurrentUser } from '../redux/slices/authSlice'

/**
 * Gate for authenticated areas. Unauthenticated users are bounced to /login
 * with the attempted path preserved for post-login redirect.
 */
export default function ProtectedRoute() {
  const { isAuthenticated, user } = useAuth()
  const dispatch = useDispatch()
  const location = useLocation()

  // Hydrate the user profile if we have a token but no cached user.
  useEffect(() => {
    if (isAuthenticated && !user) dispatch(fetchCurrentUser())
  }, [isAuthenticated, user, dispatch])

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return <Outlet />
}
