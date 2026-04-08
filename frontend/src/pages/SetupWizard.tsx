import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import i18n from '../i18n'
import { setupApi } from '../api/umay'
import '../styles/setup-wizard.css'
import { CURRENCIES } from '../constants/currencies'

const LANG_OPTIONS = [
  { code: 'tr', locale: 'tr-TR', flag: '🇹🇷', label: 'Türkçe', sub: 'Türkçe ile devam et' },
  { code: 'en', locale: 'en-US', flag: '🇬🇧', label: 'English', sub: 'Continue in English' },
  { code: 'de', locale: 'de-DE', flag: '🇩🇪', label: 'Deutsch', sub: 'Auf Deutsch fortfahren' },
]

interface SetupInitRequest {
  tenant_name: string
  tenant_slug: string
  base_currency: string
  timezone: string
  locale: string
  admin_email: string
  admin_password: string
  admin_full_name: string
  default_group_name: string
}

interface PreCheck {
  name: string
  status: 'ok' | 'warning' | 'error'
  [key: string]: unknown
}

interface SetupWizardProps {
  onComplete: () => void
}

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const { t } = useTranslation()
  const STEPS = [
    t('setup.steps.language'),
    t('setup.steps.preCheck'),
    t('setup.steps.organization'),
    t('setup.steps.admin'),
    t('setup.steps.done'),
  ]

  const [phase, setPhase] = useState<'loading' | 'language' | 'precheck' | 'form' | 'done' | 'error'>('loading')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [precheckLoading, setPrecheckLoading] = useState(false)
  const [formStep, setFormStep] = useState(0)
  const [error, setError] = useState('')
  const [prechecks, setPrechecks] = useState<PreCheck[]>([])
  const [preReady, setPreReady] = useState(false)
  const [tenantId, setTenantId] = useState('')
  const [tenantIdCopied, setTenantIdCopied] = useState(false)

  const [form, setForm] = useState<SetupInitRequest>({
    tenant_name: '',
    tenant_slug: 'default',
    base_currency: 'TRY',
    timezone: 'Europe/Istanbul',
    locale: 'tr-TR',
    admin_email: '',
    admin_password: '',
    admin_full_name: '',
    default_group_name: '',
  })

  useEffect(() => {
    setupApi.status()
      .then((res) => {
        if (res.data.initialized) {
          onComplete()
        } else {
          setPhase('language')
        }
      })
      .catch(() => {
        setPhase('error')
      })
  }, [onComplete])

  const selectedLangCode = LANG_OPTIONS.find(l => l.locale === form.locale)?.code || 'tr'

  const handleLanguageSelect = (code: string, locale: string) => {
    i18n.changeLanguage(code)
    setForm(prev => ({ ...prev, locale }))
  }

  const handleLanguageProceed = async () => {
    setPrecheckLoading(true)
    try {
      const pRes = await setupApi.precheck()
      setPrechecks(pRes.data.checks || [])
      setPreReady(pRes.data.ready_to_install)
    } catch {
      setPreReady(true)
    }
    setPrecheckLoading(false)
    setPhase('precheck')
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    if (name === 'tenant_name') {
      setForm(prev => ({
        ...prev,
        tenant_name: value,
        tenant_slug: value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'default',
      }))
    } else {
      setForm(prev => ({ ...prev, [name]: value }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError('')
    try {
      const res = await setupApi.init(form)
      const tid = res.data?.tenant_id
      if (tid) {
        const maxAge = 365 * 24 * 60 * 60
        document.cookie = `umay_tenant_id=${encodeURIComponent(tid)}; max-age=${maxAge}; path=/; samesite=lax`
        setTenantId(tid)
      }
      setPhase('done')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } | string } } })
        ?.response?.data?.detail
      const msgStr = typeof msg === 'object' ? (msg as { message?: string })?.message : msg
      setError(msgStr ?? t('setup.setupFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const copyTenantId = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(tenantId).catch(() => fallbackCopy(tenantId))
    } else {
      fallbackCopy(tenantId)
    }
    setTenantIdCopied(true)
    setTimeout(() => setTenantIdCopied(false), 2000)
  }

  const fallbackCopy = (text: string) => {
    const el = document.createElement('textarea')
    el.value = text
    el.style.position = 'fixed'
    el.style.opacity = '0'
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
  }

  const currentStep =
    phase === 'language' ? 0 :
    phase === 'precheck' ? 1 :
    phase === 'form' ? (formStep + 2) :
    phase === 'done' ? 4 : 0

  const statusIcon = (s: string) => s === 'ok' ? '✓' : s === 'warning' ? '⚠' : '✗'

  const checkLabel = (name: string) => {
    const key = `setup.precheck.${name}` as const
    const translated = t(key)
    return translated !== key ? translated : name.replace(/_/g, ' ')
  }

  if (phase === 'loading') {
    return (
      <div className="sw-root">
        <div className="sw-card sw-center">
          <div className="sw-spinner" />
          <p className="sw-hint">{t('setup.loading')}</p>
        </div>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="sw-root">
        <div className="sw-card sw-center">
          <div className="sw-error-icon">⚠</div>
          <h2>{t('common.error')}</h2>
          <p className="sw-hint">{t('setup.connectionError')}</p>
          <button className="sw-btn" onClick={() => window.location.reload()}>{t('setup.actions.retry')}</button>
        </div>
      </div>
    )
  }

  if (phase === 'done') {
    return (
      <div className="sw-root">
        <div className="sw-card">
          <div className="sw-header">
            <div className="sw-success-icon">✓</div>
            <h2>{t('setup.done')}</h2>
            <p className="sw-subtitle">{t('setup.doneDesc')}</p>
          </div>
          {tenantId && (
            <div className="sw-section">
              <h3>{t('setup.tenantId.title')}</h3>
              <p className="sw-hint">{t('setup.tenantId.desc')}</p>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8 }}>
                <code style={{
                  flex: 1, padding: '10px 12px', background: 'var(--sw-input-bg, #1a1a2e)',
                  border: '1px solid var(--sw-border, #2a2a3e)', borderRadius: 6,
                  fontFamily: 'monospace', fontSize: 13, wordBreak: 'break-all'
                }}>
                  {tenantId}
                </code>
                <button
                  className={`sw-btn${tenantIdCopied ? ' sw-btn-success' : ''}`}
                  onClick={copyTenantId}
                  style={{ whiteSpace: 'nowrap', minWidth: 100 }}
                >
                  {tenantIdCopied ? '✓ ' + t('common.copied') : '⎘ ' + t('common.copy')}
                </button>
              </div>
              <p className="sw-hint" style={{ marginTop: 8, color: 'var(--sw-warn, #f59e0b)' }}>
                ⚠ {t('setup.tenantId.warning')}
              </p>
            </div>
          )}
          <div style={{ margin: '0 24px 16px', padding: '12px 16px', background: 'var(--sw-input-bg, #1a1a2e)', borderRadius: 8, border: '1px solid var(--sw-border, #2a2a3e)' }}>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--sw-muted, #888)' }}>
              {t('setup.tenantId.contactLabel')}
            </p>
            <p style={{ margin: '4px 0 0', fontSize: 13 }}>
              <strong>Ali Köken</strong> —{' '}
              <a href="mailto:alikoken@outlook.com" style={{ color: 'var(--sw-primary, #7c3aed)' }}>
                alikoken@outlook.com
              </a>
            </p>
          </div>
          <div className="sw-actions" style={{ padding: '0 24px 24px' }}>
            <button className="sw-btn sw-btn-primary" style={{ width: '100%' }} onClick={onComplete}>
              {t('setup.tenantId.loginBtn')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="sw-root">
      <div className="sw-card">
        <div className="sw-header">
          <div className="sw-logo">U</div>
          <h1>{t('setup.welcome')}</h1>
          <p className="sw-subtitle">{t('setup.welcomeDesc')}</p>
        </div>

        <div className="sw-progress">
          {STEPS.map((label, i) => (
            <div key={i} className={`sw-step ${i === currentStep ? 'active' : i < currentStep ? 'done' : ''}`}>
              <div className="sw-step-dot">{i < currentStep ? '✓' : i + 1}</div>
              <span className="sw-step-label">{label}</span>
              {i < STEPS.length - 1 && <div className="sw-step-line" />}
            </div>
          ))}
        </div>

        {error && <div className="sw-alert">{error}</div>}

        {phase === 'language' && (
          <div className="sw-section">
            <h3>{t('setup.language.title')}</h3>
            <p className="sw-hint" style={{ margin: 0 }}>{t('setup.language.subtitle')}</p>
            <div className="sw-lang-grid">
              {LANG_OPTIONS.map(lang => (
                <button
                  key={lang.code}
                  type="button"
                  className={`sw-lang-card${selectedLangCode === lang.code ? ' selected' : ''}`}
                  onClick={() => handleLanguageSelect(lang.code, lang.locale)}
                >
                  <span className="sw-lang-flag">{lang.flag}</span>
                  <span className="sw-lang-label">{lang.label}</span>
                  <span className="sw-lang-sub">{lang.sub}</span>
                </button>
              ))}
            </div>
            <div className="sw-actions">
              <button
                className="sw-btn sw-btn-primary"
                onClick={handleLanguageProceed}
                disabled={precheckLoading}
              >
                {precheckLoading ? <span className="sw-spinner" style={{ width: 16, height: 16, borderWidth: 2, display: 'inline-block' }} /> : t('setup.language.proceed')}
              </button>
            </div>
          </div>
        )}

        {phase === 'precheck' && (
          <div className="sw-section">
            <h3>{t('setup.precheck.title')}</h3>
            <div className="sw-checks">
              {prechecks.map((check) => (
                <div key={check.name} className={`sw-check sw-check-${check.status}`}>
                  <span className="sw-check-icon">{statusIcon(check.status)}</span>
                  <div className="sw-check-body">
                    <span className="sw-check-label">{checkLabel(check.name)}</span>
                    {check.detail != null && <span className="sw-check-detail">{String(check.detail)}</span>}
                  </div>
                </div>
              ))}
            </div>
            {!preReady && <div className="sw-alert">{t('setup.precheck.criticalFail')}</div>}
            <div className="sw-actions sw-actions-split">
              <button className="sw-btn" onClick={() => setPhase('language')}>{t('setup.actions.back')}</button>
              <button
                className="sw-btn sw-btn-primary"
                onClick={() => setPhase('form')}
                disabled={!preReady}
              >
                {preReady ? t('setup.precheck.proceed') : t('setup.precheck.fixIssues')}
              </button>
            </div>
          </div>
        )}

        {phase === 'form' && formStep === 0 && (
          <form onSubmit={(e) => { e.preventDefault(); setFormStep(1) }} className="sw-section">
            <h3>{t('setup.org.title')}</h3>
            <div className="sw-field">
              <label htmlFor="tenant_name">{t('setup.org.name')}</label>
              <input id="tenant_name" name="tenant_name" type="text" value={form.tenant_name}
                onChange={handleChange} required autoFocus />
            </div>
            <div className="sw-field">
              <label htmlFor="tenant_slug">{t('setup.org.slug')}</label>
              <input id="tenant_slug" name="tenant_slug" type="text" value={form.tenant_slug}
                onChange={handleChange} pattern="[a-z0-9-]+" required />
              <span className="sw-field-hint">{t('setup.org.slugHint')}</span>
            </div>
            <div className="sw-row">
              <div className="sw-field">
                <label htmlFor="base_currency">{t('setup.org.currency')}</label>
                <select id="base_currency" name="base_currency" value={form.base_currency}
                  onChange={handleChange} required>
                  {CURRENCIES.map(c => <option key={c.code} value={c.code}>{c.trName} ({c.symbol})</option>)}
                </select>
              </div>
              <div className="sw-field">
                <label htmlFor="timezone">{t('setup.org.timezone')}</label>
                <input id="timezone" name="timezone" type="text" value={form.timezone}
                  onChange={handleChange} required />
              </div>
            </div>
            <div className="sw-field">
              <label htmlFor="default_group_name">{t('setup.org.defaultGroup')}</label>
              <input id="default_group_name" name="default_group_name" type="text"
                value={form.default_group_name} onChange={handleChange}
                placeholder={t('setup.org.defaultGroupPlaceholder')} required />
            </div>
            <div className="sw-actions sw-actions-split">
              <button type="button" className="sw-btn" onClick={() => setPhase('precheck')}>{t('setup.actions.back')}</button>
              <button type="submit" className="sw-btn sw-btn-primary">{t('setup.actions.next')}</button>
            </div>
          </form>
        )}

        {phase === 'form' && formStep === 1 && (
          <form onSubmit={handleSubmit} className="sw-section">
            <h3>{t('setup.admin.title')}</h3>
            <div className="sw-field">
              <label htmlFor="admin_full_name">{t('setup.admin.fullName')}</label>
              <input id="admin_full_name" name="admin_full_name" type="text" value={form.admin_full_name}
                onChange={handleChange} required autoFocus />
            </div>
            <div className="sw-field">
              <label htmlFor="admin_email">{t('setup.admin.email')}</label>
              <input id="admin_email" name="admin_email" type="email" value={form.admin_email}
                onChange={handleChange} required />
            </div>
            <div className="sw-field">
              <label htmlFor="admin_password">{t('setup.admin.password')}</label>
              <input id="admin_password" name="admin_password" type="password" value={form.admin_password}
                onChange={handleChange} minLength={8} required />
              <span className="sw-field-hint">{t('setup.admin.passwordHint')}</span>
            </div>
            <div className="sw-actions sw-actions-split">
              <button type="button" className="sw-btn" onClick={() => setFormStep(0)}>{t('setup.actions.back')}</button>
              <button type="submit" className="sw-btn sw-btn-primary" disabled={isSubmitting}>
                {isSubmitting ? t('setup.actions.submitting') : t('setup.actions.submit')}
              </button>
            </div>
          </form>
        )}

        {isSubmitting && (
          <div className="sw-section sw-center">
            <div className="sw-spinner" />
            <p className="sw-hint">{t('setup.actions.submitting')}</p>
          </div>
        )}
      </div>
    </div>
  )
}
