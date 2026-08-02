import { useSelector } from 'react-redux'
import { MANAGER_TYPES, USER_TYPES } from '../utils/constants'

/** Convenience selector + derived permissions for the auth slice. */
export default function useAuth() {
  const { user, status, error } = useSelector((s) => s.auth)

  return {
    user,
    companyId: user?.company ?? null,
    userType: user?.type ?? null,
    isAuthenticated: Boolean(user),
    isLoading: status === 'loading',
    isAgent: user?.type === USER_TYPES.AGENT,
    canManageUsers: MANAGER_TYPES.includes(user?.type),
    error,
  }
}
