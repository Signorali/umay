import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { usePermissions } from '../hooks/usePermissions'
import { systemApi, backupApi, exportApi, usersApi, calendarApi, updatesApi } from '../api/umay'
import { LicensePage } from './LicensePage'
import { UsersPage } from './UsersPage'
import { GroupsPage } from './GroupsPage'
import { RolesPage } from './RolesPage'
import { DeleteRequestsPage } from './DeleteRequestsPage'
import { AuditPage } from './AuditPage'
import i18n, { LANGUAGES } from '../i18n'

const LOCALE_MAP: Record<string, string> = { tr: 'tr-TR', en: 'en-US', de: 'de-DE' }
const LANG_FROM_LOCALE = (locale?: string) => {
  if (!locale) return 'tr'
  const map: Record<string, string> = { 'tr-TR': 'tr', 'en-US': 'en', 'en-GB': 'en', 'de-DE': 'de' }
  return map[locale] || locale.slice(0, 2)
}

export function SettingsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, logout, refreshUser } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { isAdmin } = usePermissions()
  const [selectedLang, setSelectedLang] = useState(() => LANG_FROM_LOCALE(user?.locale))
  const [langMsg, setLangMsg] = useState('')
  const [tab, setTab] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    const requestedTab = params.get('tab') || 'profile'
    // If non-admin tries to access admin tabs, reset to profile
    if (!isAdmin && ['backup', 'system', 'integrations'].includes(requestedTab)) {
      return 'profile'
    }
    return requestedTab
  })

  // Profile
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileMsg, setProfileMsg] = useState('')

  // Password
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwLoading, setPwLoading] = useState(false)
  const [pwMsg, setPwMsg] = useState('')
  const [pwError, setPwError] = useState('')

  // Backup
  const [backups, setBackups] = useState<any[]>([])
  const [backupLoading, setBackupLoading] = useState(false)
  const [backupMsg, setBackupMsg] = useState('')

  // System
  const [flags, setFlags] = useState<Record<string, string>>({})
  const [restoreResult, setRestoreResult] = useState<any>(null)
  const [maintenanceOn, setMaintenanceOn] = useState(false)

  // Güncelleme
  const [currentVersion, setCurrentVersion] = useState<string>('')
  const [updateInfo, setUpdateInfo] = useState<any>(null)
  const [updateLicenseKey, setUpdateLicenseKey] = useState('')
  const [updateChecking, setUpdateChecking] = useState(false)
  const [updateError, setUpdateError] = useState('')
  const [updateTriggering, setUpdateTriggering] = useState(false)
  const [updateSuccess, setUpdateSuccess] = useState('')

  // Integration credentials state
  const [creds, setCreds] = useState({ google_client_id: '', google_client_secret: '', google_redirect_uri: '', microsoft_client_id: '', microsoft_client_secret: '', microsoft_redirect_uri: '', microsoft_tenant_id: 'common' })
  const [credsLoading, setCredsLoading] = useState(false)
  const [credsSaved, setCredsSaved] = useState(false)
  const [integrations, setIntegrations] = useState<any[]>([])
  const [integrationsLoading, setIntegrationsLoading] = useState(false)
  const [extSyncing, setExtSyncing] = useState(false)

  React.useEffect(() => {
    if (tab === 'backup') {
      setBackupLoading(true)
      backupApi.list().then(r => setBackups(Array.isArray(r.data) ? r.data : [])).catch(() => {}).finally(() => setBackupLoading(false))
    }
    if (tab === 'system') {
      systemApi.flags().then(r => setFlags(r.data || {})).catch(() => {})
      systemApi.maintenance().then(r => setMaintenanceOn(r.data?.maintenance_mode ?? false)).catch(() => {})
      systemApi.getVersion().then(r => setCurrentVersion(r.data?.version || 'dev')).catch(() => {})
    }
    if (tab === 'integrations') {
      setCredsLoading(true)
      calendarApi.getCredentials().then(r => setCreds(c => ({ ...c, ...r.data }))).catch(() => {}).finally(() => setCredsLoading(false))
      setIntegrationsLoading(true)
      calendarApi.integrations().then(r => setIntegrations(r.data?.integrations || [])).catch(() => {}).finally(() => setIntegrationsLoading(false))
    }
  }, [tab])

  const handleSaveProfile = async () => {
    if (!fullName.trim()) return
    setProfileLoading(true)
    setProfileMsg('')
    try {
      await usersApi.update(user!.id, { full_name: fullName })
      setProfileMsg('✅ Profil güncellendi.')
    } catch {
      setProfileMsg('❌ Güncelleme başarısız.')
    }
    setProfileLoading(false)
  }

  const handleSaveLanguage = async () => {
    setLangMsg('')
    const locale = LOCALE_MAP[selectedLang] || 'tr-TR'
    try {
      await usersApi.updatePreferences({ locale })
      i18n.changeLanguage(selectedLang)
      await refreshUser()
      setLangMsg('✅')
    } catch {
      setLangMsg('❌')
    }
    setTimeout(() => setLangMsg(''), 2500)
  }

  const handleChangePassword = async () => {
    setPwError('')
    setPwMsg('')
    if (!currentPassword || !newPassword) { setPwError('Tüm alanları doldurun.'); return }
    if (newPassword.length < 8) { setPwError('Yeni şifre en az 8 karakter olmalı.'); return }
    if (newPassword !== confirmPassword) { setPwError('Yeni şifreler eşleşmiyor.'); return }
    setPwLoading(true)
    try {
      await usersApi.changePassword({ current_password: currentPassword, new_password: newPassword })
      setPwMsg('✅ Şifre başarıyla değiştirildi.')
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('')
    } catch (e: any) {
      setPwError(e?.response?.data?.detail || '❌ Şifre değiştirilemedi.')
    }
    setPwLoading(false)
  }

  const handleCreateBackup = async () => {
    setBackupMsg('')
    try {
      await backupApi.create()
      setBackupMsg('✅ Yedek oluşturuldu.')
      const r = await backupApi.list()
      setBackups(Array.isArray(r.data) ? r.data : [])
    } catch {
      setBackupMsg('❌ Yedek oluşturulamadı.')
    }
  }

  const handleDownloadDiag = async () => {
    try {
      const res = await exportApi.diagnostics()
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a'); a.href = url; a.download = 'umay_diagnostics.zip'; a.click()
    } catch { /* */ }
  }

  const handleValidateRestore = async () => {
    try {
      const res = await systemApi.validateRestore()
      setRestoreResult(res.data)
    } catch { /* */ }
  }

  const handleToggleMaintenance = async () => {
    try {
      if (maintenanceOn) {
        await systemApi.disableMaintenance()
        setMaintenanceOn(false)
      } else {
        await systemApi.enableMaintenance('Manual maintenance from settings')
        setMaintenanceOn(true)
      }
    } catch { /* */ }
  }

  const handleFactoryReset = async () => {
    const msg1 = 'DİKKAT: Sistemdeki TÜM veriler silinecek ve fabrika ayarlarına dönülecek. Bu işlem geri alınamaz!'
    const msg2 = 'GERÇEKTEN EMİN MİSİNİZ? Tüm hesaplar, işlemler, kullanıcılar ve ayarlar silinecek. Uygulama kurulum ekranına döneceksiniz.'
    
    if (!window.confirm(msg1)) return
    if (!window.confirm(msg2)) return
    
    try {
      await systemApi.factoryReset(true)
    } catch {
      // Backend may return 500 due to connection cleanup after schema drop,
      // but the reset itself succeeded — proceed with logout and redirect.
    }
    // Clear cookies (auth token cleared by backend logout, tenant cookie cleared here)
    document.cookie = 'umay_token=; max-age=0; path=/'
    document.cookie = 'umay_tenant_id=; max-age=0; path=/'
    window.location.href = '/'
  }

  const ALL_TABS = [
    ['profile', '👤 Profil'],
    ['security', '🔐 Şifre'],
    ['appearance', '🎨 Görünüm'],
    ['export', '📤 Dışa Aktarma'],
    ['integrations', '🔗 Entegrasyonlar'],
    ['license', '🔑 Lisans'],
    ['system', '⚙️ Sistem'],
    ['users', '👥 Kullanıcılar'],
    ['groups', '🏢 Gruplar'],
    ['roles', '🔒 Roller'],
    ['delete-requests', '🗑️ Silme İstekleri'],
    ['audit', '🛡️ Denetim'],
  ]

  const TABS = ALL_TABS.filter(([tabId]) => {
    if (['export', 'integrations', 'license', 'system', 'users', 'groups', 'roles', 'delete-requests', 'audit'].includes(tabId)) {
      return isAdmin
    }
    return true
  })

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Ayarlar</h1>
          <p className="page-subtitle">Platform yapılandırması ve kullanıcı tercihleri</p>
        </div>
      </div>

      <div className="tabs" style={{ marginBottom: 'var(--space-6)' }}>
        {TABS.map(([id, label]) => (
          <button key={id} className={`tab${tab === id ? ' active' : ''}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {/* PROFILE TAB */}
      {tab === 'profile' && (
        <div className="card" style={{ maxWidth: 520 }}>
          <div className="card-header"><div className="card-title">Profil Bilgileri</div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
              <div className="avatar avatar-lg">{user?.full_name?.slice(0, 2).toUpperCase()}</div>
              <div>
                <div style={{ fontWeight: 600 }}>{user?.full_name}</div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>{user?.email}</div>
                {user?.is_superuser && <span className="badge badge-accent" style={{ marginTop: 4 }}>Süper Kullanıcı</span>}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Ad Soyad</label>
              <input
                className="form-input"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="Ad Soyad"
              />
            </div>

            <div className="form-group">
              <label className="form-label">E-posta</label>
              <input className="form-input" value={user?.email || ''} disabled style={{ opacity: 0.6 }} />
              <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>E-posta değiştirilemez.</p>
            </div>

            <div className="form-group">
              <label className="form-label">{t('settings.language')}</label>
              <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
                <select
                  className="form-input"
                  value={selectedLang}
                  onChange={e => setSelectedLang(e.target.value)}
                  style={{ flex: 1 }}
                >
                  {LANGUAGES.map(l => (
                    <option key={l.code} value={l.code}>{l.flag} {l.label}</option>
                  ))}
                </select>
                <button className="btn btn-secondary" onClick={handleSaveLanguage} style={{ whiteSpace: 'nowrap' }}>
                  {t('common.save')} {langMsg}
                </button>
              </div>
            </div>

            {profileMsg && (
              <div style={{
                padding: '10px 14px', borderRadius: 8, fontSize: 13,
                background: profileMsg.startsWith('✅') ? '#22c55e11' : '#ef444411',
                color: profileMsg.startsWith('✅') ? '#22c55e' : '#ef4444',
              }}>{profileMsg}</div>
            )}

            <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
              <button className="btn btn-primary" onClick={handleSaveProfile} disabled={profileLoading}>
                {profileLoading ? 'Kaydediliyor...' : 'Değişiklikleri Kaydet'}
              </button>
              <button className="btn btn-danger" onClick={logout}>Çıkış Yap</button>
            </div>
          </div>
        </div>
      )}

      {/* SECURITY / PASSWORD TAB */}
      {tab === 'security' && (
        <div className="card" style={{ maxWidth: 480 }}>
          <div className="card-header"><div className="card-title">Şifre Değiştir</div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div className="form-group">
              <label className="form-label">Mevcut Şifre</label>
              <input
                className="form-input"
                type="password"
                value={currentPassword}
                onChange={e => setCurrentPassword(e.target.value)}
                placeholder="Mevcut şifrenizi girin"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Yeni Şifre</label>
              <input
                className="form-input"
                type="password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                placeholder="En az 8 karakter"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Yeni Şifre (Tekrar)</label>
              <input
                className="form-input"
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                placeholder="Yeni şifreyi tekrar girin"
              />
            </div>

            {pwError && (
              <div style={{ padding: '10px 14px', borderRadius: 8, background: '#ef444411', color: '#ef4444', fontSize: 13 }}>
                ❌ {pwError}
              </div>
            )}
            {pwMsg && (
              <div style={{ padding: '10px 14px', borderRadius: 8, background: '#22c55e11', color: '#22c55e', fontSize: 13 }}>
                {pwMsg}
              </div>
            )}

            <button className="btn btn-primary" onClick={handleChangePassword} disabled={pwLoading}>
              {pwLoading ? 'Güncelleniyor...' : 'Şifreyi Güncelle'}
            </button>
          </div>
        </div>
      )}

      {/* APPEARANCE TAB */}
      {tab === 'appearance' && (
        <div className="card" style={{ maxWidth: 420 }}>
          <div className="card-header"><div className="card-title">Görünüm</div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
              <div>
                <div style={{ fontWeight: 500 }}>Tema</div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                  Şu an: {theme === 'dark' ? '🌙 Koyu Tema' : '☀️ Açık Tema'}
                </div>
              </div>
              <button className="btn btn-secondary" onClick={toggleTheme}>
                {theme === 'dark' ? '☀️ Açık Temaya Geç' : '🌙 Koyu Temaya Geç'}
              </button>
            </div>
            <div style={{ padding: '12px 16px', background: 'var(--surface-secondary)', borderRadius: 10, fontSize: 13, color: 'var(--text-secondary)' }}>
              💡 Tema tercihiniz tarayıcıda saklanır.
            </div>
          </div>
        </div>
      )}

      {/* BACKUP TAB */}
      {tab === 'backup' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div className="card" style={{ maxWidth: 700 }}>
            <div className="card-header">
              <div className="card-title">Veritabanı Yedekleri</div>
              <button className="btn btn-primary btn-sm" onClick={handleCreateBackup}>+ Yeni Yedek</button>
            </div>
            {backupMsg && (
              <div style={{
                padding: '10px 14px', margin: '0 0 12px', borderRadius: 8, fontSize: 13,
                background: backupMsg.startsWith('✅') ? '#22c55e11' : '#ef444411',
                color: backupMsg.startsWith('✅') ? '#22c55e' : '#ef4444',
              }}>{backupMsg}</div>
            )}
            {backupLoading ? (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>Yedekler yükleniyor...</div>
            ) : backups.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--space-8)' }}>
                <div className="empty-state-icon">💾</div>
                <div className="empty-state-title">Henüz yedek yok</div>
              </div>
            ) : (
              <table className="data-table">
                <thead><tr><th>Dosya</th><th>Boyut</th><th>Tarih</th></tr></thead>
                <tbody>
                  {backups.map((b: any) => (
                    <tr key={b.filename}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>{b.filename}</td>
                      <td>{b.size_bytes ? (b.size_bytes / 1024 / 1024).toFixed(1) + ' MB' : '—'}</td>
                      <td style={{ fontSize: 'var(--font-size-xs)' }}>
                        {b.created_at ? new Date(b.created_at).toLocaleString('tr-TR') : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div style={{ padding: '12px 16px', background: '#f59e0b11', borderRadius: 10, border: '1px solid #f59e0b44', fontSize: 13, color: '#f59e0b', maxWidth: 700 }}>
            ⚠️ Tam yedek yönetimi için <strong>Yönetim → Yedekleme</strong> sayfasını kullanın.
          </div>
        </div>
      )}

      {/* EXPORT TAB */}
      {tab === 'export' && (
        <div className="card" style={{ maxWidth: 520 }}>
          <div className="card-header"><div className="card-title">Veri Dışa Aktarma</div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {[
              ['📊 İşlemleri CSV İndir', () => exportApi.transactionsCsv().then(r => { const url = URL.createObjectURL(r.data); const a = document.createElement('a'); a.href = url; a.download = 'transactions.csv'; a.click() })],
              ['🏦 Hesapları CSV İndir', () => exportApi.accountsCsv().then(r => { const url = URL.createObjectURL(r.data); const a = document.createElement('a'); a.href = url; a.download = 'accounts.csv'; a.click() })],
              ['📦 Tam JSON Dışa Aktar', () => exportApi.fullJson().then(r => { const url = URL.createObjectURL(r.data); const a = document.createElement('a'); a.href = url; a.download = 'umay_export.json'; a.click() })],
              ['🔧 Tanı Paketi İndir (ZIP)', handleDownloadDiag],
            ].map(([label, fn]: any) => (
              <button key={String(label)} className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={fn}>
                {label}
              </button>
            ))}
            <div style={{ marginTop: 8, padding: '10px 14px', background: 'var(--surface-secondary)', borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
              💡 Dışa aktarılan veriler yalnızca size aittir. İstediğiniz zaman indirebilirsiniz.
            </div>
          </div>
        </div>
      )}

      {/* INTEGRATIONS TAB */}
      {tab === 'integrations' && (() => {
        const googleConnected = integrations.find(i => i.provider === 'google')
        const msConnected = integrations.find(i => i.provider === 'microsoft')
        const googleReady = !!(creds.google_client_id && creds.google_redirect_uri)
        const msReady = !!(creds.microsoft_client_id && creds.microsoft_redirect_uri)

        const StepBadge = ({ n, done }: { n: number; done: boolean }) => (
          <div style={{
            width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 700,
            background: done ? '#22c55e22' : 'var(--surface-secondary)',
            color: done ? '#22c55e' : 'var(--text-secondary)',
            border: `2px solid ${done ? '#22c55e44' : 'var(--border)'}`,
          }}>
            {done ? '✓' : n}
          </div>
        )

        const ProviderCard = ({
          icon, title, color, accent,
          connected, connectedAccount, lastSync,
          step1Guide, step1Link, step1LinkLabel,
          credFields, onSaveCredentials, hasCreds,
          onConnect, onDisconnect, onSync, syncing,
        }: any) => (
          <div className="card" style={{ maxWidth: 800, borderTop: `3px solid ${accent}` }}>
            {/* Header: provider logo + status */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 28 }}>{icon}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 16 }}>{title}</div>
                  <div style={{ fontSize: 12, marginTop: 2 }}>
                    {connected
                      ? <span style={{ color: '#22c55e' }}>● Bağlı — <strong>{connectedAccount}</strong>{lastSync && <span style={{ color: 'var(--text-tertiary)', marginLeft: 8 }}>Son sync: {lastSync}</span>}</span>
                      : <span style={{ color: 'var(--text-tertiary)' }}>● Bağlı değil</span>}
                  </div>
                </div>
              </div>
              {connected && (
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-secondary btn-sm" disabled={syncing} onClick={onSync}>
                    {syncing ? '↻ Senkronize ediliyor...' : '↻ Şimdi Senkronize Et'}
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={onDisconnect}>Bağlantıyı Kes</button>
                </div>
              )}
            </div>

            {connected ? (
              /* ── Already connected: show sync info ── */
              <div style={{ padding: '14px 16px', background: '#22c55e11', border: '1px solid #22c55e33', borderRadius: 10, fontSize: 13, color: '#22c55e' }}>
                ✅ Takvim bağlantısı aktif. Finansal ödeme ve gelir etkinlikleriniz her 15 dakikada bir otomatik olarak senkronize edilmektedir.
              </div>
            ) : (
              /* ── Not connected: 3-step setup ── */
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

                {/* Step 1 */}
                <div style={{ display: 'flex', gap: 16 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <StepBadge n={1} done={false} />
                    <div style={{ width: 2, flex: 1, background: 'var(--border)', borderRadius: 2 }} />
                  </div>
                  <div style={{ paddingBottom: 20 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Geliştirici hesabında uygulama oluşturun</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 10 }}>
                      {step1Guide}
                    </div>
                    <a href={step1Link} target="_blank" rel="noreferrer"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: accent, fontWeight: 500, textDecoration: 'none', padding: '6px 12px', background: `${accent}15`, borderRadius: 7, border: `1px solid ${accent}33` }}>
                      ↗ {step1LinkLabel}
                    </a>
                  </div>
                </div>

                {/* Step 2 */}
                <div style={{ display: 'flex', gap: 16 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <StepBadge n={2} done={hasCreds} />
                    <div style={{ width: 2, flex: 1, background: 'var(--border)', borderRadius: 2 }} />
                  </div>
                  <div style={{ flex: 1, paddingBottom: 20 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Uygulama kimlik bilgilerini buraya girin</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                      Oluşturduğunuz uygulamanın <strong>Client ID</strong> ve <strong>Client Secret</strong> değerlerini aşağıya girin, sonra kaydedin.
                    </div>
                    {credsLoading ? (
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Yükleniyor...</div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {credFields}
                        <div>
                          <button className="btn btn-primary btn-sm" onClick={onSaveCredentials}>
                            💾 Kimlik Bilgilerini Kaydet
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Step 3 */}
                <div style={{ display: 'flex', gap: 16 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <StepBadge n={3} done={false} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Hesabınızla giriş yaparak bağlayın</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                      Kimlik bilgilerini kaydettikten sonra aşağıdaki butona tıklayın. Hesap seçim ekranı açılacak, izin verdikten sonra bağlantı otomatik kurulacak.
                    </div>
                    <button
                      className="btn btn-primary"
                      disabled={!hasCreds}
                      onClick={onConnect}
                      style={{ opacity: hasCreds ? 1 : 0.45, cursor: hasCreds ? 'pointer' : 'not-allowed' }}
                    >
                      {icon} {title.split(' ')[0]} Hesabıyla Bağlan
                    </button>
                    {!hasCreds && (
                      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 6 }}>
                        ⚠️ Önce 2. adımdaki kimlik bilgilerini kaydetmeniz gerekiyor.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )

        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>

            {/* Intro */}
            <div style={{ maxWidth: 800, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              Google Takvim veya Microsoft Outlook ile bağlantı kurarak finansal ödeme ve gelirlerin takvime otomatik eklenmesini sağlayabilirsiniz.
              Her sağlayıcı için aşağıdaki <strong>3 adımı</strong> izleyin.
            </div>

            {/* Google Card */}
            <ProviderCard
              icon="🟢" title="Google Takvim" color="#22c55e" accent="#4285F4"
              connected={googleConnected}
              connectedAccount={googleConnected?.email}
              lastSync={googleConnected?.last_synced_at ? new Date(googleConnected.last_synced_at).toLocaleString('tr-TR') : null}
              step1Guide={
                <>
                  <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" style={{ color: '#4285F4' }}>Google Cloud Console</a>'u açın →
                  sol menüden <strong>APIs & Services → Credentials</strong> seçin →
                  <strong> + Create Credentials → OAuth client ID</strong> tıklayın →
                  uygulama türü olarak <strong>Web application</strong> seçin →
                  <strong> Authorized redirect URIs</strong> alanına aşağıda gireceğiniz Redirect URI'yi ekleyin →
                  oluşturulan <strong>Client ID</strong> ve <strong>Client Secret</strong>'ı kopyalayın.
                </>
              }
              step1Link="https://console.cloud.google.com/apis/credentials"
              step1LinkLabel="Google Cloud Console'u Aç"
              hasCreds={googleReady}
              credFields={
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label">Client ID</label>
                      <input className="form-input" placeholder="xxxx.apps.googleusercontent.com"
                        value={creds.google_client_id} onChange={e => setCreds(c => ({ ...c, google_client_id: e.target.value }))} />
                    </div>
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label">Client Secret</label>
                      <input className="form-input" type="password" placeholder="GOCSPX-..."
                        value={creds.google_client_secret} onChange={e => setCreds(c => ({ ...c, google_client_secret: e.target.value }))} />
                    </div>
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">
                      Redirect URI
                      <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-tertiary)', marginLeft: 6 }}>
                        (Google Console'daki Authorized redirect URI ile aynı olmalı)
                      </span>
                    </label>
                    <input className="form-input" placeholder={`${window.location.origin}/api/v1/calendar/integrations/google/callback`}
                      value={creds.google_redirect_uri} onChange={e => setCreds(c => ({ ...c, google_redirect_uri: e.target.value }))} />
                  </div>
                </div>
              }
              onSaveCredentials={async () => {
                try {
                  await calendarApi.saveCredentials({ google_client_id: creds.google_client_id, google_client_secret: creds.google_client_secret, google_redirect_uri: creds.google_redirect_uri })
                  setCredsSaved(true); setTimeout(() => setCredsSaved(false), 3000)
                } catch { /* */ }
              }}
              onConnect={() => calendarApi.connectGoogle()}
              onDisconnect={async () => { await calendarApi.disconnect('google'); const r = await calendarApi.integrations(); setIntegrations(r.data?.integrations || []) }}
              onSync={async () => { setExtSyncing(true); try { await calendarApi.syncExternal() } catch { /* */ } finally { setExtSyncing(false); const r = await calendarApi.integrations(); setIntegrations(r.data?.integrations || []) }}}
              syncing={extSyncing}
            />

            {/* Microsoft Card */}
            <ProviderCard
              icon="🔵" title="Microsoft Outlook Takvim" color="#0078D4" accent="#0078D4"
              connected={msConnected}
              connectedAccount={msConnected?.email}
              lastSync={msConnected?.last_synced_at ? new Date(msConnected.last_synced_at).toLocaleString('tr-TR') : null}
              step1Guide={
                <>
                  <a href="https://portal.azure.com/" target="_blank" rel="noreferrer" style={{ color: '#0078D4' }}>Azure Portal</a>'ı açın →
                  sol menüden <strong>Microsoft Entra ID → App registrations</strong> seçin →
                  <strong> + New registration</strong> tıklayın → uygulamaya bir ad verin →
                  <strong> Redirect URI</strong> alanına aşağıda gireceğiniz URI'yi ekleyin →
                  kayıt sonrası <strong>Application (client) ID</strong>'yi kopyalayın →
                  <strong> Certificates & secrets → + New client secret</strong> ile secret oluşturun.
                </>
              }
              step1Link="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
              step1LinkLabel="Azure Portal'ı Aç"
              hasCreds={msReady}
              credFields={
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label">Application (Client) ID</label>
                      <input className="form-input" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                        value={creds.microsoft_client_id} onChange={e => setCreds(c => ({ ...c, microsoft_client_id: e.target.value }))} />
                    </div>
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label">Client Secret</label>
                      <input className="form-input" type="password" placeholder="Azure'da oluşturulan secret değeri"
                        value={creds.microsoft_client_secret} onChange={e => setCreds(c => ({ ...c, microsoft_client_secret: e.target.value }))} />
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label">
                        Redirect URI
                        <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-tertiary)', marginLeft: 6 }}>
                          (Azure → Authentication → Redirect URIs ile aynı olmalı)
                        </span>
                      </label>
                      <input className="form-input" placeholder={`${window.location.origin}/api/v1/calendar/integrations/microsoft/callback`}
                        value={creds.microsoft_redirect_uri} onChange={e => setCreds(c => ({ ...c, microsoft_redirect_uri: e.target.value }))} />
                    </div>
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label">
                        Tenant ID
                        <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-tertiary)', marginLeft: 6 }}>
                          (kişisel = common)
                        </span>
                      </label>
                      <input className="form-input" placeholder="common"
                        value={creds.microsoft_tenant_id} onChange={e => setCreds(c => ({ ...c, microsoft_tenant_id: e.target.value }))} />
                    </div>
                  </div>
                </div>
              }
              onSaveCredentials={async () => {
                try {
                  await calendarApi.saveCredentials({ microsoft_client_id: creds.microsoft_client_id, microsoft_client_secret: creds.microsoft_client_secret, microsoft_redirect_uri: creds.microsoft_redirect_uri, microsoft_tenant_id: creds.microsoft_tenant_id })
                  setCredsSaved(true); setTimeout(() => setCredsSaved(false), 3000)
                } catch { /* */ }
              }}
              onConnect={() => calendarApi.connectMicrosoft()}
              onDisconnect={async () => { await calendarApi.disconnect('microsoft'); const r = await calendarApi.integrations(); setIntegrations(r.data?.integrations || []) }}
              onSync={async () => { setExtSyncing(true); try { await calendarApi.syncExternal() } catch { /* */ } finally { setExtSyncing(false); const r = await calendarApi.integrations(); setIntegrations(r.data?.integrations || []) }}}
              syncing={extSyncing}
            />

            <div style={{ fontSize: 12, color: 'var(--text-tertiary)', maxWidth: 800 }}>
              💡 Bağlantı kurulduktan sonra finansal takvim etkinlikleri her 15 dakikada bir arka planda otomatik senkronize edilir.
            </div>
          </div>
        )
      })()}

      {/* LICENSE TAB */}
      {tab === 'license' && <LicensePage />}

      {/* USERS TAB */}
      {tab === 'users' && <UsersPage />}

      {/* GROUPS TAB */}
      {tab === 'groups' && <GroupsPage />}

      {/* ROLES TAB */}
      {tab === 'roles' && <RolesPage />}

      {/* DELETE REQUESTS TAB */}
      {tab === 'delete-requests' && <DeleteRequestsPage />}

      {/* AUDIT TAB */}
      {tab === 'audit' && <AuditPage />}

      {/* SYSTEM TAB */}
      {tab === 'system' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>

          {/* Yazılım Sürümü / Güncelleme */}
          <div className="card" style={{ maxWidth: 700 }}>
            <div className="card-header">
              <div className="card-title">Yazılım Sürümü</div>
              {updateInfo?.has_update && (
                <span className="badge" style={{ background: '#ef4444', color: '#fff' }}>🔴 Güncelleme var</span>
              )}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 13 }}>
                <span>Kurulu sürüm: <strong>{currentVersion || '—'}</strong></span>
                {updateInfo?.latest_version && (
                  <span>Güncel sürüm: <strong>{updateInfo.latest_version}</strong></span>
                )}
              </div>

              {!updateInfo ? (
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'flex-end' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={updateChecking}
                    onClick={async () => {
                      setUpdateChecking(true)
                      setUpdateError('')
                      try {
                        const r = await updatesApi.status()
                        setUpdateInfo(r.data)
                      } catch (e: any) {
                        setUpdateError(e?.response?.data?.detail || 'Güncelleme kontrol edilemedi. Lisans geçerli mi kontrol edin.')
                      } finally { setUpdateChecking(false) }
                    }}
                  >
                    {updateChecking ? 'Kontrol ediliyor...' : '🔍 Güncelleme Kontrol Et'}
                  </button>
                </div>
              ) : updateInfo.has_update ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: 'var(--space-3)' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>v{updateInfo.latest_version} — Değişiklikler:</div>
                    {(updateInfo.changelog || []).map((c: string, i: number) => (
                      <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)' }}>• {c}</div>
                    ))}
                  </div>
                  {updateSuccess && (
                    <div style={{ fontSize: 12, background: '#22c55e22', color: '#22c55e', padding: '8px 12px', borderRadius: 6 }}>
                      ✅ {updateSuccess}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={updateTriggering}
                      onClick={async () => {
                        setUpdateTriggering(true)
                        setUpdateSuccess('')
                        setUpdateError('')
                        try {
                          await updatesApi.trigger()
                          setUpdateSuccess('Güncelleme başladı... Sistem biraz zaman sonra kendini güncelleyecektir.')
                          setTimeout(() => {
                            setUpdateInfo(null)
                            setUpdateLicenseKey('')
                          }, 3000)
                        } catch (e: any) {
                          setUpdateError(e?.response?.data?.detail || 'Güncelleme başlatılamadı')
                        } finally {
                          setUpdateTriggering(false)
                        }
                      }}
                    >
                      {updateTriggering ? '⏳ Başlatılıyor...' : '🚀 Şimdi Güncelle'}
                    </button>
                    <button className="btn btn-ghost btn-sm" onClick={() => { setUpdateInfo(null); }}>
                      Yeniden kontrol et
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--income)', fontSize: 13 }}>
                  ✅ Sistem güncel ({updateInfo.latest_version})
                  <button className="btn btn-ghost btn-sm" onClick={() => { setUpdateInfo(null); }}>Yenile</button>
                </div>
              )}

              {updateError && (
                <div style={{ color: 'var(--expense)', fontSize: 12 }}>❌ {updateError}</div>
              )}
            </div>
          </div>

          {/* Maintenance Mode */}
          <div className="card" style={{ maxWidth: 700 }}>
            <div className="card-header">
              <div className="card-title">Bakım Modu</div>
              <button
                className={`btn btn-sm ${maintenanceOn ? 'btn-danger' : 'btn-secondary'}`}
                onClick={handleToggleMaintenance}
              >
                {maintenanceOn ? '🔴 Bakım Modunu Kapat' : '🟡 Bakım Modunu Aç'}
              </button>
            </div>
            <div style={{ padding: '12px 0', fontSize: 13, color: 'var(--text-secondary)' }}>
              {maintenanceOn
                ? '⚠️ Sistem bakım modunda. Yeni kullanıcı işlemleri engelleniyor.'
                : '✅ Sistem normal çalışıyor.'}
            </div>
          </div>

          {/* System Flags */}
          <div className="card" style={{ maxWidth: 700 }}>
            <div className="card-header"><div className="card-title">Sistem Bayrakları</div></div>
            {Object.keys(flags).length === 0 ? (
              <div style={{ padding: '16px 0', color: 'var(--text-secondary)', fontSize: 13 }}>Hiç bayrak yok.</div>
            ) : (
              <table className="data-table">
                <thead><tr><th>Bayrak</th><th>Değer</th></tr></thead>
                <tbody>
                  {Object.entries(flags).map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>{k}</td>
                      <td>{v || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Restore Validation */}
          <div className="card" style={{ maxWidth: 700 }}>
            <div className="card-header">
              <div className="card-title">Geri Yükleme Doğrulaması</div>
              <button className="btn btn-secondary btn-sm" onClick={handleValidateRestore}>Kontrolleri Çalıştır</button>
            </div>
            {restoreResult && (
              <div className={`alert ${restoreResult.overall === 'ok' ? 'alert-success' : 'alert-danger'}`} style={{ marginTop: 'var(--space-4)' }}>
                <strong>Genel Durum: {restoreResult.overall?.toUpperCase()}</strong>
                <pre style={{ marginTop: 8, fontSize: 11, overflowX: 'auto' }}>
                  {JSON.stringify(restoreResult.checks, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Factory Reset */}
          {user?.is_superuser && (
            <div className="card" style={{ maxWidth: 700, border: '1px solid #ef444444' }}>
              <div className="card-header">
                <div className="card-title" style={{ color: 'var(--danger)' }}>Fabrika Ayarlarına Sıfırla</div>
                <button className="btn btn-danger btn-sm" onClick={handleFactoryReset}>Sistemi Sıfırla</button>
              </div>
              <div style={{ padding: '12px 0', fontSize: 13, color: 'var(--text-secondary)' }}>
                ⚠️ Bu işlem veritabanındaki tüm tabloları siler ve yeniden oluşturur. 
                Tüm verileriniz (hesaplar, işlemler, kullanıcılar) kalıcı olarak kaybolacaktır.
                İşlem tamamlandığında sistem kurulum sihirbazına yönlendirileceksiniz.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SettingsPage
