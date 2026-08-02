import { useCallback, useEffect, useState } from 'react'
import { STORAGE_KEYS } from '../utils/constants'
import { storage } from '../utils/storage'

/**
 * Dark-mode controller. Toggles the `dark` class on <html> (Tailwind
 * darkMode: 'class') and persists the choice. Defaults to system preference.
 */
function getInitialTheme() {
  const saved = storage.get(STORAGE_KEYS.THEME)
  if (saved === 'light' || saved === 'dark') return saved
  const prefersDark =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: dark)').matches
  return prefersDark ? 'dark' : 'light'
}

export default function useTheme() {
  const [theme, setTheme] = useState(getInitialTheme)

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', theme === 'dark')
    storage.set(STORAGE_KEYS.THEME, theme)
  }, [theme])

  const toggleTheme = useCallback(
    () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')),
    [],
  )

  return { theme, setTheme, toggleTheme, isDark: theme === 'dark' }
}
