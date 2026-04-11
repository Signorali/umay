import React, { useEffect, useState } from 'react'
import { licenseApi } from '../api/umay'
import { useAuth } from '../context/AuthContext'
import { LicenseIcon, BuildingIcon } from '../components/Icons'

interface LicenseStatus {
  is_licensed: boolean
  plan: string
  issued_to: string
  max_users: number
  features: string[]
  issued_at: string | null
  expires_at: string | null
  days_until_expiry: number | null
  is_expired: boolean
  license_id: string | null
}


const PLAN_LABELS: Record<string, string> = {
  trial:        'Deneme',
  starter:      'Starter',
  professional: 'Professional',
  enterprise:   'Enterprise',
}

export function LicensePage() {
  const { user } = useAuth()
  const [license, setLicense] = useState<LicenseStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [activateKey, setActivateKey] = useState('')
  const [activating, setActivating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [tenantIdCopied, setTenantIdCopied] = useState(false)

  const copyTenantId = () => {
    const id = user?.tenant_id || ''
    if (navigator.clipboard) {
      navigator.clipboard.writeText(id).catch(() => fallbackCopy(id))
    } else {
      fallbackCopy(id)
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

  useEffect(() => { loadLicense() }, [])

  const loadLicense = async () => {
    setLoading(true)
    try {
      const res = await licenseApi.status()
      setLicense(res.data)
    } catch { /* bağlantı hatası */ }
    setLoading(false)
  }

  const activateLicense = async () => {
    if (!activateKey.trim()) return
    setActivating(true)
    setError('')
    setSuccess('')
    try {
      await licenseApi.activate(activateKey.trim())
      setSuccess('Lisans başarıyla etkinleştirildi.')
      setActivateKey('')
      await loadLicense()
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      const msg = typeof detail === 'object' ? detail?.message : detail
      setError(msg || 'Etkinleştirme başarısız. Anahtarı kontrol edin.')
    }
    setActivating(false)
  }

  const fmt = (iso: string | null) => iso ? new Date(iso).toLocaleDateString('tr-TR') : '—'
  const days = license?.days_until_expiry ?? null
  const statusColor = !license?.is_licensed
    ? { bg: '#6b728022', text: '#6b7280', label: 'Deneme Modu' }
    : license.is_expired
    ? { bg: '#ef444422', text: '#ef4444', label: 'Süresi Dolmuş' }
    : { bg: '#22c55e22', text: '#22c55e', label: 'Aktif' }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 800 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Lisans Yönetimi</h1>
        <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: 14 }}>
          Umay kurulum lisansınızı yönetin
        </p>
      </div>

      {error && (
        <div style={{ background: '#ef444422', border: '1px solid #ef4444', borderRadius: 10, padding: '12px 16px',
          color: '#ef4444', marginBottom: 16, fontSize: 14 }}>⚠️ {error}</div>
      )}
      {success && (
        <div style={{ background: '#22c55e22', border: '1px solid #22c55e', borderRadius: 10, padding: '12px 16px',
          color: '#22c55e', marginBottom: 16, fontSize: 14 }}>✅ {success}</div>
      )}

      {/* Current License Card */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-secondary)' }}>Yükleniyor...</div>
      ) : license ? (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 28, marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
                {PLAN_LABELS[license.plan] || license.plan}
              </div>
              {license.issued_to && (
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{license.issued_to}</div>
              )}
            </div>
            <span style={{ padding: '6px 16px', borderRadius: 20, fontWeight: 700, fontSize: 13,
              background: statusColor.bg, color: statusColor.text }}>
              {statusColor.label}
            </span>
          </div>

          {/* Süre uyarısı */}
          {days !== null && (
            <div style={{
              padding: '12px 16px', borderRadius: 10, marginBottom: 20,
              background: days < 7 ? '#ef444411' : days < 30 ? '#f59e0b11' : '#22c55e11',
              border: `1px solid ${days < 7 ? '#ef444444' : days < 30 ? '#f59e0b44' : '#22c55e44'}`,
              color: days < 7 ? '#ef4444' : days < 30 ? '#f59e0b' : '#22c55e', fontSize: 13,
            }}>
              {license.is_expired
                ? '❌ Lisans süresi dolmuş'
                : days === 0
                ? '⚠️ Lisans bugün sona eriyor'
                : `⏱️ ${days} gün kaldı (${fmt(license.expires_at)})`}
            </div>
          )}

          {/* Detay grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Plan', value: PLAN_LABELS[license.plan] },
              { label: 'Durum', value: statusColor.label },
              { label: 'Maks. Kullanıcı', value: license.max_users >= 9999 ? 'Sınırsız' : String(license.max_users) },
              { label: 'Bitiş', value: license.expires_at ? fmt(license.expires_at) : 'Süresiz ♾️' },
              { label: 'Lisans ID', value: license.license_id ? license.license_id.substring(0, 12) + '...' : '—' },
              { label: 'Başlangıç', value: fmt(license.issued_at) },
            ].map(item => (
              <div key={item.label} style={{ padding: '12px 14px', background: 'var(--surface-secondary)',
                borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 600,
                  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>{item.label}</div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{item.value || '—'}</div>
              </div>
            ))}
          </div>

          {/* Özellikler */}
          {license.features.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-tertiary)',
                textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Aktif Özellikler</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {license.features.map(f => (
                  <span key={f} style={{ padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                    background: '#22c55e22', color: '#22c55e' }}>✓ {f}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 36,
          textAlign: 'center', marginBottom: 24 }}>
          <div style={{ marginBottom: 12, color: 'var(--text-tertiary)' }}><LicenseIcon size={48} /></div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Lisans Bulunamadı</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Sisteminiz lisanssız çalışıyor. Deneme modu aktif.</div>
        </div>
      )}

      {/* Tenant ID */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24, marginBottom: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}><BuildingIcon size={15} /> Tenant ID</div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Lisans anahtarı almak için bu kimliği satıcınıza gönderin.
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <code style={{ flex: 1, padding: '10px 14px', borderRadius: 10, border: '1px solid var(--border)',
            background: 'var(--surface-secondary)', fontFamily: 'monospace', fontSize: 13,
            color: 'var(--text-primary)', wordBreak: 'break-all' }}>
            {user?.tenant_id || '—'}
          </code>
          <button onClick={copyTenantId} style={{
            padding: '10px 18px', borderRadius: 10, border: '1px solid var(--border)',
            background: tenantIdCopied ? '#22c55e22' : 'var(--surface-secondary)',
            color: tenantIdCopied ? '#22c55e' : 'var(--text-primary)',
            cursor: 'pointer', fontWeight: 600, fontSize: 13, whiteSpace: 'nowrap',
          }}>
            {tenantIdCopied ? '✓ Kopyalandı' : '⎘ Kopyala'}
          </button>
        </div>
      </div>

      {/* Activate License */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}><LicenseIcon size={15} /> Lisans Etkinleştir</div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14 }}>
          Satıcınızdan aldığınız UMAY.1. ile başlayan anahtarı girin.
        </div>
        <textarea
          value={activateKey}
          onChange={e => setActivateKey(e.target.value)}
          placeholder="UMAY.1...."
          rows={4}
          style={{
            width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid var(--border)',
            background: 'var(--surface-secondary)', color: 'var(--text-primary)', fontSize: 12,
            fontFamily: 'monospace', resize: 'vertical', boxSizing: 'border-box', marginBottom: 12,
          }}
        />
        <button onClick={activateLicense} disabled={activating || !activateKey.trim()} style={{
          width: '100%', padding: '12px', borderRadius: 10, border: 'none',
          cursor: activating || !activateKey.trim() ? 'not-allowed' : 'pointer',
          background: 'var(--accent)', color: '#fff', fontWeight: 700, fontSize: 14,
          opacity: activateKey.trim() ? 1 : 0.5,
        }}>
          {activating ? 'Etkinleştiriliyor...' : 'Etkinleştir'}
        </button>
      </div>
    </div>
  )
}

export default LicensePage
