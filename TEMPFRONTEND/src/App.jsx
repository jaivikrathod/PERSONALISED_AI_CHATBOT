import { useEffect } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { Provider, useDispatch } from 'react-redux'
import store from './redux/store'
import AppRoutes from './routes/AppRoutes'
import Toaster from './components/ui/Toaster'
import useTheme from './hooks/useTheme'
import { restoreSession } from './redux/slices/authSlice'

/** Applies the persisted theme to <html> once on mount. */
function ThemeBootstrap() {
  useTheme()
  return null
}

/**
 * Re-validates the stored token against the server on load. The cached profile
 * is only good for first paint — this is what stops a revoked or expired
 * session from leaving the UI looking signed in.
 */
function SessionBootstrap() {
  const dispatch = useDispatch()
  useEffect(() => {
    dispatch(restoreSession())
  }, [dispatch])
  return null
}

export default function App() {
  return (
    <Provider store={store}>
      <ThemeBootstrap />
      <SessionBootstrap />
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <AppRoutes />
      </BrowserRouter>
      <Toaster />
    </Provider>
  )
}
