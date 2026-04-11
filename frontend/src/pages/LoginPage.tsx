import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { authApi } from '../api/umay'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { LANGUAGES } from '../i18n'
import { AppearanceIcon, MoonIcon } from '../components/Icons'

export function LoginPage() {
  const { login } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { t, i18n } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // Read tenant_id from cookie (set by App.tsx on setup status check, not sensitive)
  const tenantId = document.cookie.split('; ').reduce((acc, part) => {
    const [k, v] = part.split('='); return k === 'umay_tenant_id' ? decodeURIComponent(v || '') : acc
  }, '')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.login(email, password, tenantId)
      // Backend sets httpOnly cookie — just call login() to fetch /auth/me
      await login(res.data.access_token, res.data.refresh_token)
    } catch {
      setError(t('login.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100dvh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-base)',
      padding: 'var(--space-4)',
      position: 'relative',
    }}>
      {/* Top-right controls */}
      <div style={{ position: 'absolute', top: 'var(--space-5)', right: 'var(--space-6)', display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
        {/* Lang switcher */}
        {LANGUAGES.map(lang => (
          <button
            key={lang.code}
            onClick={() => i18n.changeLanguage(lang.code)}
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 18, opacity: i18n.language === lang.code ? 1 : 0.4, padding: '2px 4px' }}
            title={lang.label}
          >{lang.flag}</button>
        ))}
        <button
          onClick={toggleTheme}
          className="btn btn-ghost btn-icon"
        >
          {theme === 'dark' ? <AppearanceIcon size={16} /> : <MoonIcon size={16} />}
        </button>
      </div>

      {/* Glow */}
      <div style={{
        position: 'absolute', top: '20%', left: '50%', transform: 'translateX(-50%)',
        width: 400, height: 400,
        background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{
        width: '100%',
        maxWidth: 400,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-xl)',
        padding: 'var(--space-10)',
        boxShadow: 'var(--shadow-lg)',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
          <div style={{
            width: 56, height: 56,
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, var(--accent), #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, fontWeight: 800, color: 'white',
            margin: '0 auto var(--space-4)',
            boxShadow: 'var(--shadow-accent)',
          }}>U</div>
          <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 6 }}>
            {t('login.title')}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
            {t('login.subtitle')}
          </p>
        </div>

        {error && (
          <div className="alert alert-danger" style={{ marginBottom: 'var(--space-5)' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div className="form-group">
            <label className="form-label" htmlFor="login-email">{t('login.email')}</label>
            <input
              id="login-email"
              type="email"
              className="form-input"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder={t('login.emailPlaceholder')}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="login-password">{t('login.password')}</label>
            <input
              id="login-password"
              type="password"
              className="form-input"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg"
            style={{ width: '100%', marginTop: 'var(--space-2)' }}
            disabled={loading}
          >
            {loading ? (
              <><span className="spinner spinner-sm" /> {t('login.loggingIn')}</>
            ) : (
              t('login.loginBtn')
            )}
          </button>
        </form>

        {!tenantId && (
          <div className="alert alert-warning" style={{ marginTop: 'var(--space-4)', fontSize: 'var(--font-size-xs)' }}>
            ⚠️ Tenant not detected. Run the setup wizard first.
          </div>
        )}
      </div>
    </div>
  )
}
