import { useSelector } from 'react-redux'

/** Convenience selector for the auth slice. */
export default function useAuth() {
  const { user, accessToken, status, error } = useSelector((s) => s.auth)
  return {
    user,
    isAuthenticated: Boolean(accessToken),
    isLoading: status === 'loading',
    error,
  }
}
