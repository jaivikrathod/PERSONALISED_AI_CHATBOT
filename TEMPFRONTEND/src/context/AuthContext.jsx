import { createContext, useContext, useMemo, useState } from 'react'
import { userStore } from '../utils/storage'

/**
 * Minimal auth context. The logged-in user (returned by the login endpoint)
 * is kept in state and mirrored to localStorage so a refresh keeps the session.
 */
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => userStore.get())

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      login(loggedInUser) {
        userStore.set(loggedInUser)
        setUser(loggedInUser)
      },
      logout() {
        userStore.clear()
        setUser(null)
      },
    }),
    [user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
