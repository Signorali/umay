import React, { useEffect, useState } from 'react'
import { periodLockApi } from '../api/umay'

const MONTHS = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']

export function PeriodLockPage() {
  const [lockedPeriods, setLockedPeriods] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [confirm, setConfirm] = useState<{ year: number; month: number; action: 'lock' | 'unlock' } | null>(null)

  const currentYear = new Date().getFullYear()
  const years = [currentYear - 2, currentYear - 1, currentYear]

  useEffect(() => { loadPeriods() }, [])

  const loadPeriods = async () => {
    setLoading(true)
    try {
      const res = await periodLockApi.getLockedPeriods()
      setLockedPeriods(res.data?.locked_periods || [])
    } catch { setError('Dönem verileri yüklenemedi.') }
    setLoading(false)
  }

  const isPeriodKey = (y: number, m: number) => `${y}-${String(m).padStart(2, '0')}`
  const isLocked = (y: number, m: number) => lockedPeriods.includes(isPeriodKey(y, m))
  const isFuture = (y: number, m: number) => {
    const now = new Date()
    return y > now.getFullYear() || (y === now.getFullYear() && m > now.getMonth() + 1)
  }

  const handleAction = async () => {
    if (!confirm) return
    const key = isPeriodKey(confirm.year, confirm.month)
    setActionLoading(key)
    try {
      if (confirm.action === 'lock') {
        await periodLockApi.lockPeriod(confirm.year, confirm.month)
      } else {
        await periodLockApi.unlockPeriod(confirm.year, confirm.month)
      }
      await loadPeriods()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'İşlem başarısız.')
    }
    setActionLoading(null)
    setConfirm(null)
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Dönem Kilitleme</h1>
        <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.5 }}>
          Kapatılan muhasebe dönemleri kilitlenir — kilitli dönemlerde işlem oluşturulamaz, güncellenemez veya silinemez.
        </p>
      </div>

      {error && (
        <div style={{ background: '#ef444422', border: '1px solid #ef4444', borderRadius: 10, padding: '12px 16px',
          color: '#ef4444', marginBottom: 20, fontSize: 14 }}>
          ⚠️ {error}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 28 }}>
        {[
          { label: 'Kilitli Dönem', value: lockedPeriods.length, color: '#ef4444' },
          { label: 'Açık Dönem', value: years.length * 12 - lockedPeriods.length, color: '#22c55e' },
        ].map(s => (
          <div key={s.label} style={{
            background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
            padding: '16px 24px', flex: 1,
          }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
          padding: '16px 24px', flex: 2,
        }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8, fontWeight: 600 }}>KILITLI DÖNEMLER</div>
          {lockedPeriods.length === 0 ? (
            <span style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Henüz kilitli dönem yok</span>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {lockedPeriods.map(p => (
                <span key={p} style={{
                  background: '#ef444422', color: '#ef4444', padding: '3px 10px',
                  borderRadius: 20, fontSize: 12, fontWeight: 600,
                }}>{p}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Year grids */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>Yükleniyor...</div>
      ) : years.map(year => (
        <div key={year} style={{
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14,
          padding: 20, marginBottom: 16,
        }}>
          <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 16, color: 'var(--text-primary)' }}>{year}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8 }}>
            {MONTHS.map((month, idx) => {
              const m = idx + 1
              const locked = isLocked(year, m)
              const future = isFuture(year, m)
              const actionKey = isPeriodKey(year, m)
              const busy = actionLoading === actionKey

              return (
                <div key={m} style={{
                  borderRadius: 10, border: `1px solid ${locked ? '#ef444444' : 'var(--border)'}`,
                  background: locked ? '#ef444411' : future ? 'var(--surface-secondary)' : 'var(--surface)',
                  padding: '12px 8px', textAlign: 'center', transition: 'all 0.2s',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: locked ? '#ef4444' : future ? 'var(--text-tertiary)' : 'var(--text-primary)', marginBottom: 6 }}>
                    {month}
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    {locked ? (
                      <span style={{ fontSize: 18 }}>🔒</span>
                    ) : future ? (
                      <span style={{ fontSize: 18 }}>⏳</span>
                    ) : (
                      <span style={{ fontSize: 18 }}>🔓</span>
                    )}
                  </div>
                  {!future && (
                    <button
                      disabled={busy}
                      onClick={() => setConfirm({ year, month: m, action: locked ? 'unlock' : 'lock' })}
                      style={{
                        padding: '4px 10px', borderRadius: 6, border: 'none', cursor: busy ? 'not-allowed' : 'pointer',
                        fontSize: 11, fontWeight: 600,
                        background: locked ? '#22c55e22' : '#ef444422',
                        color: locked ? '#22c55e' : '#ef4444',
                      }}>
                      {busy ? '...' : locked ? 'Aç' : 'Kilitle'}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {/* Confirm Modal */}
      {confirm && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div style={{
            background: 'var(--surface)', borderRadius: 16, padding: 32, maxWidth: 420, width: '90%',
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: 20, marginBottom: 16 }}>
              {confirm.action === 'lock' ? '🔒 Dönemi Kilitle' : '🔓 Dönemi Aç'}
            </div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 24, fontSize: 14 }}>
              <strong>{MONTHS[confirm.month - 1]} {confirm.year}</strong> dönemini{' '}
              {confirm.action === 'lock'
                ? 'kilitlemek istediğinize emin misiniz? Kilitli dönemde işlem değişikliği yapılamaz.'
                : 'yeniden açmak istediğinize emin misiniz? Bu işlem denetim kaydında görünecektir.'}
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button onClick={() => setConfirm(null)} style={{
                padding: '10px 20px', borderRadius: 8, border: '1px solid var(--border)',
                background: 'var(--surface-secondary)', cursor: 'pointer', color: 'var(--text-primary)', fontWeight: 600,
              }}>İptal</button>
              <button onClick={handleAction} style={{
                padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 700,
                background: confirm.action === 'lock' ? '#ef4444' : '#22c55e', color: '#fff',
              }}>
                {confirm.action === 'lock' ? 'Kilitle' : 'Aç'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PeriodLockPage
