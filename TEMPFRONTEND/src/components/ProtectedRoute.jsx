import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/** Redirects to /login when there is no authenticated user. */
export default function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}
