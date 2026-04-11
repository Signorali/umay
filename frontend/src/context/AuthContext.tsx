import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi } from '../api/umay'
import i18n from '../i18n'

const LOCALE_TO_LANG: Record<string, string> = {
  'tr-TR': 'tr',
  'en-US': 'en',
  'en-GB': 'en',
  'de-DE': 'de',
}

interface UserResponse {
  id: string
  email: string
  full_name: string
  is_superuser: boolean
  is_tenant_admin: boolean
  tenant_id: string
  ui_theme?: string
  locale?: string
  dashboard_layout?: string
  permissions: string[]       // ['module:action', ...] or ['*'] for admins
  must_change_password: boolean
}

interface AuthContextValue {
  user: UserResponse | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (accessToken: string, refreshToken: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const fetchUser = async () => {
    try {
      const res = await authApi.me()
      setUser(res.data)
      if (res.data.locale) {
        const lang = LOCALE_TO_LANG[res.data.locale] || res.data.locale.slice(0, 2)
        i18n.changeLanguage(lang)
      }
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    // Token is in httpOnly cookie — just call /auth/me and let the browser send it
    fetchUser()
  }, [])

  const login = async (_accessToken: string, _refreshToken: string) => {
    // Cookies are set by the backend on login response — just fetch user info
    const res = await authApi.me()
    setUser(res.data)
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch {
      // Sunucu hatası olsa bile çıkışa devam et
    }
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
      refreshUser: fetchUser,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
