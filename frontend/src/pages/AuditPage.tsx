import React, { useEffect, useState, useCallback } from 'react'
import { auditApi } from '../api/umay'

interface AuditLog {
  id: string
  created_at: string
  actor_email: string | null
  action: string
  module: string
  record_id: string | null
  before_data: string | null
  after_data: string | null
  ip_address: string | null
  notes: string | null
}

const ACTION_COLORS: Record<string, string> = {
  CREATE: '#22c55e',
  UPDATE: '#3b82f6',
  DELETE: '#ef4444',
  LOGIN: '#8b5cf6',
  LOGIN_FAILED: '#f97316',
  PERIOD_LOCK: '#f59e0b',
  PERIOD_UNLOCK: '#06b6d4',
  PERMISSION_CHANGED: '#ec4899',
  FACTORY_RESET: '#dc2626',
  CSV_IMPORT: '#14b8a6',
}

export function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState<'all' | 'security'>('all')
  const [filters, setFilters] = useState({ module: '', action: '', record_id: '' })
  const [expanded, setExpanded] = useState<string | null>(null)

  const PAGE_SIZE = 50

  const load = useCallback(async () => {
    setLoading(true)
    try {
      if (view === 'security') {
        const res = await auditApi.securityEvents({ limit: PAGE_SIZE })
        setLogs(res.data.items || [])
        setTotal(res.data.total || (res.data.items?.length ?? 0))
      } else {
        const params: Record<string, string | number> = { page, page_size: PAGE_SIZE }
        if (filters.module) params.module = filters.module
        if (filters.action) params.action = filters.action
        if (filters.record_id) params.record_id = filters.record_id
        const res = await auditApi.list(params)
        setLogs(res.data.items || [])
        setTotal(res.data.total || 0)
      }
    } catch { /* ignore */ }
    setLoading(false)
  }, [page, view, filters])


  useEffect(() => { load() }, [load])

  const fmt = (iso: string) => new Date(iso).toLocaleString('tr-TR')
  const actionColor = (a: string) => ACTION_COLORS[a] || '#6b7280'

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1400 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Denetim Kaydı</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: 14 }}>
            Sistemdeki tüm kritik değişiklikler kayıt altında — {total.toLocaleString()} kayıt
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {(['all', 'security'] as const).map(v => (
            <button key={v} onClick={() => { setView(v); setPage(1) }}
              style={{
                padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600,
                background: view === v ? 'var(--accent)' : 'var(--surface-secondary)',
                color: view === v ? '#fff' : 'var(--text-primary)', fontSize: 13,
              }}>
              {v === 'all' ? 'Tüm Kayıtlar' : '🔐 Güvenlik'}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { key: 'module', placeholder: 'Modül (transactions, accounts...)' },
          { key: 'action', placeholder: 'Aksiyon (CREATE, UPDATE, LOGIN...)' },
          { key: 'record_id', placeholder: 'Kayıt ID' },
        ].map(f => (
          <input key={f.key}
            value={filters[f.key as keyof typeof filters]}
            onChange={e => { setFilters(p => ({ ...p, [f.key]: e.target.value })); setPage(1) }}
            placeholder={f.placeholder}
            style={{
              padding: '8px 14px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--surface)', color: 'var(--text-primary)', fontSize: 13, minWidth: 200,
            }}
          />
        ))}
        <button onClick={load} style={{
          padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
          background: 'var(--surface-secondary)', color: 'var(--text-primary)', fontSize: 13,
        }}>🔄 Yenile</button>
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', borderRadius: 12, border: '1px solid var(--border)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--surface-secondary)', borderBottom: '1px solid var(--border)' }}>
              {['Zaman', 'Aksiyon', 'Modül', 'Kullanıcı', 'Kayıt ID', 'IP', ''].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: 12, fontWeight: 600,
                  color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>Yükleniyor...</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>Kayıt bulunamadı</td></tr>
            ) : logs.map(log => (
              <React.Fragment key={log.id}>
                <tr style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-secondary)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ padding: '10px 16px', fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{fmt(log.created_at)}</td>
                  <td style={{ padding: '10px 16px' }}>
                    <span style={{
                      padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                      background: actionColor(log.action) + '22', color: actionColor(log.action),
                    }}>{log.action}</span>
                  </td>
                  <td style={{ padding: '10px 16px', fontSize: 13 }}>{log.module}</td>
                  <td style={{ padding: '10px 16px', fontSize: 13, color: 'var(--text-secondary)' }}>{log.actor_email || '—'}</td>
                  <td style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-tertiary)', fontFamily: 'monospace' }}>
                    {log.record_id ? log.record_id.substring(0, 8) + '...' : '—'}
                  </td>
                  <td style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-tertiary)' }}>{log.ip_address || '—'}</td>
                  <td style={{ padding: '10px 16px' }}>
                    {(log.before_data || log.after_data) && (
                      <button onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)', fontSize: 12 }}>
                        {expanded === log.id ? '▲ Gizle' : '▼ Detay'}
                      </button>
                    )}
                  </td>
                </tr>
                {expanded === log.id && (
                  <tr style={{ background: 'var(--surface-secondary)' }}>
                    <td colSpan={7} style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        {log.before_data && (
                          <div>
                            <div style={{ fontSize: 11, fontWeight: 700, color: '#ef4444', marginBottom: 6 }}>ÖNCE</div>
                            <pre style={{ margin: 0, fontSize: 11, overflow: 'auto', maxHeight: 200,
                              background: 'var(--surface)', padding: 12, borderRadius: 8, color: 'var(--text-secondary)' }}>
                              {JSON.stringify(JSON.parse(log.before_data), null, 2)}
                            </pre>
                          </div>
                        )}
                        {log.after_data && (
                          <div>
                            <div style={{ fontSize: 11, fontWeight: 700, color: '#22c55e', marginBottom: 6 }}>SONRA</div>
                            <pre style={{ margin: 0, fontSize: 11, overflow: 'auto', maxHeight: 200,
                              background: 'var(--surface)', padding: 12, borderRadius: 8, color: 'var(--text-secondary)' }}>
                              {JSON.stringify(JSON.parse(log.after_data), null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 20 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--surface)', cursor: page === 1 ? 'not-allowed' : 'pointer', color: 'var(--text-primary)' }}>
            ‹ Önceki
          </button>
          <span style={{ padding: '8px 16px', color: 'var(--text-secondary)', fontSize: 13 }}>
            {page} / {Math.ceil(total / PAGE_SIZE)}
          </span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * PAGE_SIZE >= total}
            style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--surface)', cursor: page * PAGE_SIZE >= total ? 'not-allowed' : 'pointer', color: 'var(--text-primary)' }}>
            Sonraki ›
          </button>
        </div>
      )}
    </div>
  )
}

export default AuditPage
