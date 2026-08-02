import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'react-redux'
import store from './redux/store'
import AppRoutes from './routes/AppRoutes'
import Toaster from './components/ui/Toaster'
import useTheme from './hooks/useTheme'

/** Applies the persisted theme to <html> once on mount. */
function ThemeBootstrap() {
  useTheme()
  return null
}

export default function App() {
  return (
    <Provider store={store}>
      <ThemeBootstrap />
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
      <Toaster />
    </Provider>
  )
}
