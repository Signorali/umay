import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { LANGUAGES } from '../i18n'
import { NotificationBell } from './NotificationBell'

export function Topbar({ title }: { title?: string }) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { t, i18n } = useTranslation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [langOpen, setLangOpen] = useState(false)

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()
    : 'U'

  const currentLang = LANGUAGES.find(l => l.code === i18n.language) || LANGUAGES[0]

  const handleLangChange = (code: string) => {
    i18n.changeLanguage(code)
    setLangOpen(false)
  }

  return (
    <header className="app-topbar">
      {/* Page title slot */}
      <div style={{ flex: 1 }}>
        {title && (
          <span style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', color: 'var(--text-secondary)' }}>
            {title}
          </span>
        )}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>

        {/* Language switcher */}
        <div className="dropdown" style={{ position: 'relative' }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setLangOpen(o => !o)}
            style={{ fontSize: 14, gap: 4, display: 'flex', alignItems: 'center' }}
            title={t('settings.language')}
          >
            <span style={{ fontSize: 18 }}>{currentLang.flag}</span>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{currentLang.code.toUpperCase()}</span>
          </button>

          {langOpen && (
            <>
              <div
                style={{ position: 'fixed', inset: 0, zIndex: 199 }}
                onClick={() => setLangOpen(false)}
              />
              <div className="dropdown-menu" style={{ minWidth: 140, right: 0, left: 'auto' }}>
                {LANGUAGES.map(lang => (
                  <button
                    key={lang.code}
                    className={`dropdown-item ${i18n.language === lang.code ? 'active' : ''}`}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
                      fontWeight: i18n.language === lang.code ? 600 : 400,
                      color: i18n.language === lang.code ? 'var(--accent)' : undefined,
                    }}
                    onClick={() => handleLangChange(lang.code)}
                  >
                    <span style={{ fontSize: 18 }}>{lang.flag}</span>
                    <span>{lang.label}</span>
                    {i18n.language === lang.code && <span style={{ marginLeft: 'auto', fontSize: 10 }}>✓</span>}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Theme toggle */}
        <button
          className="btn btn-ghost btn-icon btn-sm"
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}
          style={{ fontSize: 16 }}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>

        {/* Notifications */}
        <NotificationBell />

        {/* User menu */}
        <div className="dropdown">
          <button
            className="avatar"
            onClick={() => setMenuOpen(o => !o)}
            style={{ cursor: 'pointer', border: 'none', fontSize: 'var(--font-size-xs)' }}
          >
            {initials}
          </button>

          {menuOpen && (
            <>
              <div
                style={{ position: 'fixed', inset: 0, zIndex: 199 }}
                onClick={() => setMenuOpen(false)}
              />
              <div className="dropdown-menu">
                <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                    {user?.full_name || 'User'}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>
                    {user?.email}
                  </div>
                </div>
                <button className="dropdown-item" onClick={() => { setMenuOpen(false); window.location.href = '/settings' }}>
                  ⚙️ &nbsp;{t('nav.settings')}
                </button>
                <div className="dropdown-divider" />
                <button className="dropdown-item danger" onClick={() => { logout(); setMenuOpen(false) }}>
                  🚪 &nbsp;{t('nav.logout')}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
