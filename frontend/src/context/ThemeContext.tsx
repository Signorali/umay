import React, { createContext, useContext, useEffect, useState } from 'react'
import { usersApi } from '../api/umay'

type Theme = 'dark' | 'light'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'dark',
  toggleTheme: () => {},
})

export function ThemeProvider({ children, initialTheme }: { children: React.ReactNode; initialTheme?: string }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('umay_theme') as Theme
    if (saved === 'dark' || saved === 'light') return saved
    return (initialTheme as Theme) || 'dark'
  })

  // Watch for changes in initialTheme (e.g. after user profile loads from DB)
  // to sync cross-device settings
  useEffect(() => {
    if (initialTheme && (initialTheme === 'dark' || initialTheme === 'light')) {
      const saved = localStorage.getItem('umay_theme')
      // Only apply if user preference loaded and we don't have it locally,
      // or if it changed upstream. If we trust user db, we sync.
      // We check if it changed from what we currently have if we don't want to override.
      // The safest is just to let local override, but wait, 
      // if initialTheme comes in after loading, we should adopt it.
      if (initialTheme !== theme) {
        setTheme(initialTheme)
        localStorage.setItem('umay_theme', initialTheme)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTheme])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('umay_theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(t => {
      const next = t === 'dark' ? 'light' : 'dark'
      localStorage.setItem('umay_theme', next)
      // Persist to DB — fire and forget
      usersApi.updatePreferences({ ui_theme: next }).catch(() => {})
      return next
    })
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeContext)
